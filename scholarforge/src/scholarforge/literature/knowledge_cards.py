"""Knowledge Card Extraction from paper abstracts."""

from ..llm.provider import LLMProvider
from ..utils.logger import get_logger
from .models import KnowledgeCard, PaperResult

logger = get_logger(__name__)


def _extract_from_paper(
    topic: str,
    paper: PaperResult,
    llm: LLMProvider
) -> KnowledgeCard:
    """Extract knowledge from a single paper.
    
    Args:
        topic: Research topic
        paper: Paper to analyze
        llm: LLM provider
        
    Returns:
        KnowledgeCard with extracted information
    """
    system = """You are an academic paper analyzer. Extract structured information from paper abstracts. Be precise and factual — only extract what the abstract explicitly states. Do not infer or embellish.

Respond ONLY in valid JSON matching this schema:
{
  "key_findings": ["finding 1", "finding 2"],
  "methodology": "brief description of the method",
  "datasets_used": ["dataset1", "dataset2"],
  "baselines_compared": ["method1", "method2"],
  "limitations": ["limitation1"],
  "relevance_to_topic": "one sentence on how this relates to the topic"
}"""

    user = f"""Research Topic: {topic}

Paper: {paper.title}
Authors: {', '.join(paper.authors[:5])}
Abstract: {paper.abstract}"""

    try:
        result = llm.complete_json(system, user)
        
        return KnowledgeCard(
            paper=paper,
            key_findings=result.get("key_findings", []),
            methodology=result.get("methodology", ""),
            datasets_used=result.get("datasets_used", []),
            baselines_compared=result.get("baselines_compared", []),
            limitations=result.get("limitations", []),
            relevance_to_topic=result.get("relevance_to_topic", "")
        )
    except Exception as e:
        logger.warning(f"Knowledge extraction failed for '{paper.title}': {e}")
        # Return empty card
        return KnowledgeCard(
            paper=paper,
            relevance_to_topic="Extraction failed"
        )


def extract_knowledge_cards(
    topic: str,
    papers: list[PaperResult],
    llm: LLMProvider,
    batch_size: int = 5
) -> list[KnowledgeCard]:
    """Extract knowledge cards from multiple papers.
    
    Args:
        topic: Research topic
        papers: List of papers to analyze
        llm: LLM provider
        batch_size: Number of papers to process in each batch
        
    Returns:
        List of KnowledgeCard objects
    """
    logger.info(f"Extracting knowledge from {len(papers)} papers (batch_size={batch_size})")
    
    cards: list[KnowledgeCard] = []
    
    for i, paper in enumerate(papers):
        logger.debug(f"Processing paper {i+1}/{len(papers)}: {paper.title[:50]}...")
        
        card = _extract_from_paper(topic, paper, llm)
        cards.append(card)
        
        # Log progress periodically
        if (i + 1) % batch_size == 0:
            logger.info(f"Processed {i + 1}/{len(papers)} papers")
    
    logger.info(f"Extracted {len(cards)} knowledge cards")
    return cards
