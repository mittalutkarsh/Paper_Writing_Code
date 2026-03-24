"""arXiv Search Client.

Library: `arxiv` (pip install arxiv)
API: export.arxiv.org/api/query (no API key required)
"""

from datetime import datetime
from typing import Optional

import arxiv

from ..utils.logger import get_logger
from .models import PaperResult

logger = get_logger(__name__)


def search_arxiv(
    query: str, 
    categories: list[str], 
    max_results: int = 30,
    year_range: Optional[tuple[int, int]] = None
) -> list[PaperResult]:
    """Search arXiv for papers matching the query.
    
    Args:
        query: Search query string
        categories: List of arXiv categories (e.g., ["cs.AI", "cs.LG"])
        max_results: Maximum number of results to return
        year_range: Optional (start_year, end_year) tuple
        
    Returns:
        List of PaperResult objects
    """
    logger.info(f"Searching arXiv: query='{query}', categories={categories}, max_results={max_results}")
    
    # Build category filter
    if categories:
        cat_filter = " OR ".join([f"cat:{cat}" for cat in categories])
        full_query = f"({query}) AND ({cat_filter})"
    else:
        full_query = query
    
    # Configure client with rate limiting
    client = arxiv.Client(
        page_size=100,
        delay_seconds=3.0,
        num_retries=3
    )
    
    # Build search
    search = arxiv.Search(
        query=full_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    
    results: list[PaperResult] = []
    
    try:
        for result in client.results(search):
            # Filter by year if specified
            if year_range:
                year = result.published.year
                if year < year_range[0] or year > year_range[1]:
                    continue
            
            paper = PaperResult(
                title=result.title,
                authors=[a.name for a in result.authors],
                abstract=result.summary,
                arxiv_id=result.entry_id.split("/abs/")[-1],
                doi=result.doi,
                pdf_url=result.pdf_url,
                published_date=result.published,
                source="arxiv",
                categories=[c for c in result.categories],
                citation_count=None,  # Not available from arXiv
                year=result.published.year
            )
            results.append(paper)
            
            if len(results) >= max_results:
                break
                
    except Exception as e:
        logger.error(f"arXiv search error: {e}")
        raise
    
    logger.info(f"Found {len(results)} papers from arXiv")
    return results


def get_arxiv_paper_by_id(arxiv_id: str) -> Optional[PaperResult]:
    """Fetch a specific paper by arXiv ID.
    
    Args:
        arxiv_id: arXiv paper ID (e.g., "2301.07041v1")
        
    Returns:
        PaperResult if found, None otherwise
    """
    client = arxiv.Client(delay_seconds=3.0, num_retries=3)
    
    try:
        search = arxiv.Search(id_list=[arxiv_id.split('v')[0]])  # Remove version
        result = next(client.results(search))
        
        return PaperResult(
            title=result.title,
            authors=[a.name for a in result.authors],
            abstract=result.summary,
            arxiv_id=result.entry_id.split("/abs/")[-1],
            doi=result.doi,
            pdf_url=result.pdf_url,
            published_date=result.published,
            source="arxiv",
            categories=[c for c in result.categories],
            year=result.published.year
        )
    except StopIteration:
        logger.warning(f"arXiv paper not found: {arxiv_id}")
        return None
    except Exception as e:
        logger.error(f"Error fetching arXiv paper {arxiv_id}: {e}")
        return None
