"""Search Orchestrator — Combines all search sources."""

from difflib import SequenceMatcher

from ..config import LiteratureConfig
from ..llm.provider import LLMProvider
from ..utils.logger import get_logger
from .arxiv_search import search_arxiv
from .models import PaperResult
from .semantic_scholar import search_s2

logger = get_logger(__name__)


def _fuzzy_match_title(title1: str, title2: str, threshold: float = 0.90) -> bool:
    """Check if two titles are likely the same paper.
    
    Args:
        title1: First title
        title2: Second title
        threshold: Similarity threshold (0.0-1.0)
        
    Returns:
        True if titles match above threshold
    """
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio() >= threshold


def _deduplicate_papers(papers: list[PaperResult]) -> list[PaperResult]:
    """Deduplicate papers by DOI, arXiv ID, or fuzzy title match.
    
    Args:
        papers: List of papers (may contain duplicates)
        
    Returns:
        Deduplicated list, preferring papers with more metadata
    """
    seen: dict[str, PaperResult] = {}
    
    for paper in papers:
        # Try to match by DOI
        if paper.doi:
            key = f"doi:{paper.doi.lower()}"
            if key in seen:
                # Merge metadata, keeping the one with more info
                existing = seen[key]
                if _paper_has_more_metadata(paper, existing):
                    seen[key] = _merge_papers(paper, existing)
                else:
                    seen[key] = _merge_papers(existing, paper)
                continue
            seen[key] = paper
            continue
        
        # Try to match by arXiv ID
        if paper.arxiv_id:
            key = f"arxiv:{paper.arxiv_id.lower()}"
            if key in seen:
                existing = seen[key]
                if _paper_has_more_metadata(paper, existing):
                    seen[key] = _merge_papers(paper, existing)
                else:
                    seen[key] = _merge_papers(existing, paper)
                continue
            seen[key] = paper
            continue
        
        # Try fuzzy title match
        is_duplicate = False
        for existing_key, existing in seen.items():
            if _fuzzy_match_title(paper.title, existing.title):
                if _paper_has_more_metadata(paper, existing):
                    seen[existing_key] = _merge_papers(paper, existing)
                else:
                    seen[existing_key] = _merge_papers(existing, paper)
                is_duplicate = True
                break
        
        if not is_duplicate:
            seen[f"title:{paper.title.lower()[:50]}"] = paper
    
    return list(seen.values())


def _paper_has_more_metadata(p1: PaperResult, p2: PaperResult) -> bool:
    """Check if p1 has more complete metadata than p2."""
    score1 = sum([
        1 if p1.doi else 0,
        1 if p1.arxiv_id else 0,
        1 if p1.citation_count is not None else 0,
        1 if p1.venue else 0,
        1 if len(p1.abstract) > 100 else 0
    ])
    score2 = sum([
        1 if p2.doi else 0,
        1 if p2.arxiv_id else 0,
        1 if p2.citation_count is not None else 0,
        1 if p2.venue else 0,
        1 if len(p2.abstract) > 100 else 0
    ])
    return score1 > score2


def _merge_papers(primary: PaperResult, secondary: PaperResult) -> PaperResult:
    """Merge two papers, taking the best from each."""
    return PaperResult(
        title=primary.title if len(primary.title) >= len(secondary.title) else secondary.title,
        authors=primary.authors if len(primary.authors) >= len(secondary.authors) else secondary.authors,
        abstract=primary.abstract if len(primary.abstract) >= len(secondary.abstract) else secondary.abstract,
        arxiv_id=primary.arxiv_id or secondary.arxiv_id,
        doi=primary.doi or secondary.doi,
        pdf_url=primary.pdf_url or secondary.pdf_url,
        published_date=primary.published_date or secondary.published_date,
        source=f"{primary.source},{secondary.source}" if primary.source != secondary.source else primary.source,
        categories=primary.categories if primary.categories else secondary.categories,
        citation_count=primary.citation_count if primary.citation_count is not None else secondary.citation_count,
        venue=primary.venue or secondary.venue,
        year=primary.year or secondary.year
    )


def _score_relevance(
    topic: str,
    paper: PaperResult,
    llm: LLMProvider
) -> tuple[float, str]:
    """Score paper relevance using LLM.
    
    Args:
        topic: Research topic
        paper: Paper to score
        llm: LLM provider
        
    Returns:
        Tuple of (score, reason)
    """
    system = """You are a research paper relevance scorer. Given a research topic and a paper's title + abstract, score relevance from 0.0 to 1.0.

Scoring criteria:
- 0.9-1.0: Directly addresses the same problem or method
- 0.7-0.8: Closely related methodology or application domain
- 0.5-0.6: Related but tangential (useful for Related Work)
- 0.3-0.4: Loosely related, provides background context only
- 0.0-0.2: Not relevant

Respond ONLY in valid JSON: {"score": 0.85, "reason": "brief explanation"}"""

    user = f"""Topic: {topic}

Paper Title: {paper.title}
Authors: {', '.join(paper.authors[:3])}
Abstract: {paper.abstract[:1000]}"""

    try:
        result = llm.complete_json(system, user)
        score = float(result.get("score", 0.0))
        reason = result.get("reason", "")
        return max(0.0, min(1.0, score)), reason
    except Exception as e:
        logger.warning(f"Relevance scoring failed for '{paper.title}': {e}")
        return 0.5, "Scoring failed"


def search_all(
    topic: str,
    config: LiteratureConfig,
    llm: LLMProvider
) -> list[PaperResult]:
    """Search across all configured sources and return ranked results.
    
    Args:
        topic: Research topic
        config: Literature search configuration
        llm: LLM provider for relevance scoring
        
    Returns:
        Deduplicated, relevance-ranked list of papers
    """
    logger.info(f"Starting literature search for topic: {topic}")
    
    all_papers: list[PaperResult] = []
    
    # Search arXiv
    if "arxiv" in config.search_sources:
        try:
            arxiv_papers = search_arxiv(
                query=topic,
                categories=config.arxiv_categories,
                max_results=config.max_papers
            )
            all_papers.extend(arxiv_papers)
            logger.info(f"Found {len(arxiv_papers)} papers from arXiv")
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
    
    # Search Semantic Scholar
    if "semantic_scholar" in config.search_sources:
        try:
            s2_api_key = config.get_s2_api_key()
            s2_papers = search_s2(
                query=topic,
                max_results=config.max_papers,
                api_key=s2_api_key
            )
            all_papers.extend(s2_papers)
            logger.info(f"Found {len(s2_papers)} papers from Semantic Scholar")
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
    
    # Deduplicate
    deduplicated = _deduplicate_papers(all_papers)
    logger.info(f"After deduplication: {len(deduplicated)} unique papers")
    
    # Score relevance for each paper
    scored_papers: list[tuple[PaperResult, float, str]] = []
    for paper in deduplicated:
        score, reason = _score_relevance(topic, paper, llm)
        scored_papers.append((paper, score, reason))
        logger.debug(f"Relevance {score:.2f} for '{paper.title[:50]}...': {reason}")
    
    # Sort by relevance score
    scored_papers.sort(key=lambda x: x[1], reverse=True)
    
    # Filter by threshold and limit
    filtered = [
        paper for paper, score, _ in scored_papers
        if score >= config.relevance_threshold
    ][:config.max_papers]
    
    logger.info(f"Returning {len(filtered)} papers above relevance threshold {config.relevance_threshold}")
    return filtered
