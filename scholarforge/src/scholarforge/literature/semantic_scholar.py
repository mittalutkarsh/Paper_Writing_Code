"""Semantic Scholar Search Client.

API: api.semanticscholar.org/graph/v1/
Rate limits: 5,000 requests per 5 minutes (unauthenticated)
"""

import time
from typing import Optional

import requests

from ..utils.logger import get_logger
from .models import PaperResult

logger = get_logger(__name__)

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,authors,abstract,externalIds,citationCount,year,openAccessPdf,venue,tldr"

# Rate limiting
_last_request_time = 0.0
_min_interval = 0.2  # 5 requests per second max


def _rate_limited_request(url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> dict:
    """Make a rate-limited request to S2 API."""
    global _last_request_time
    
    # Enforce rate limit
    elapsed = time.time() - _last_request_time
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    
    response = requests.get(url, params=params, headers=headers, timeout=15)
    _last_request_time = time.time()
    
    if response.status_code == 429:
        logger.warning("S2 rate limit hit, waiting 5 seconds...")
        time.sleep(5)
        return _rate_limited_request(url, params, headers)
    
    response.raise_for_status()
    return response.json()


def search_s2(
    query: str,
    max_results: int = 30,
    year_range: Optional[tuple[int, int]] = None,
    fields_of_study: Optional[list[str]] = None,
    api_key: Optional[str] = None
) -> list[PaperResult]:
    """Search Semantic Scholar for papers.
    
    Args:
        query: Search query string
        max_results: Maximum number of results
        year_range: Optional (start_year, end_year) tuple
        fields_of_study: Optional list of fields (e.g., ["Computer Science"])
        api_key: Optional S2 API key for higher rate limits
        
    Returns:
        List of PaperResult objects
    """
    logger.info(f"Searching Semantic Scholar: query='{query}', max_results={max_results}")
    
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    
    results: list[PaperResult] = []
    offset = 0
    batch_size = 100
    
    while len(results) < max_results:
        params = {
            "query": query,
            "limit": min(batch_size, max_results - len(results)),
            "offset": offset,
            "fields": FIELDS
        }
        
        try:
            data = _rate_limited_request(
                f"{BASE_URL}/paper/search",
                params=params,
                headers=headers
            )
            
            papers = data.get("data", [])
            if not papers:
                break
            
            for paper in papers:
                # Filter by year if specified
                year = paper.get("year")
                if year_range and year:
                    if year < year_range[0] or year > year_range[1]:
                        continue
                
                external_ids = paper.get("externalIds", {})
                open_access = paper.get("openAccessPdf")
                tldr = paper.get("tldr", {})
                
                # Use TLDR if available and abstract is short
                abstract = paper.get("abstract", "")
                if tldr and tldr.get("text") and len(abstract) < 100:
                    abstract = tldr["text"]
                
                authors = []
                for author in paper.get("authors", []):
                    name = author.get("name")
                    if name:
                        authors.append(name)
                
                result = PaperResult(
                    title=paper.get("title", ""),
                    authors=authors,
                    abstract=abstract or "",
                    arxiv_id=external_ids.get("ArXiv"),
                    doi=external_ids.get("DOI"),
                    pdf_url=open_access.get("url") if open_access else None,
                    source="semantic_scholar",
                    citation_count=paper.get("citationCount"),
                    venue=paper.get("venue"),
                    year=year
                )
                results.append(result)
                
                if len(results) >= max_results:
                    break
            
            offset += len(papers)
            
            # Check if there are more results
            total = data.get("total", 0)
            if offset >= total:
                break
                
        except requests.RequestException as e:
            logger.error(f"S2 search error: {e}")
            break
    
    logger.info(f"Found {len(results)} papers from Semantic Scholar")
    return results


def batch_lookup_s2(
    paper_ids: list[str],
    api_key: Optional[str] = None
) -> list[PaperResult]:
    """Batch lookup papers by IDs.
    
    Args:
        paper_ids: List of paper IDs (DOI:xxx, ArXiv:xxx, CorpusID:xxx, S2 paper ID, or URL)
        api_key: Optional S2 API key
        
    Returns:
        List of PaperResult objects (may be fewer than input if some not found)
    """
    logger.info(f"Batch lookup of {len(paper_ids)} papers")
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    
    results: list[PaperResult] = []
    batch_size = 500  # S2 batch limit
    
    for i in range(0, len(paper_ids), batch_size):
        batch = paper_ids[i:i + batch_size]
        
        try:
            # Enforce rate limit
            time.sleep(_min_interval)
            
            response = requests.post(
                f"{BASE_URL}/paper/batch",
                headers=headers,
                json={"ids": batch},
                params={"fields": FIELDS},
                timeout=30
            )
            response.raise_for_status()
            
            papers = response.json()
            for paper in papers:
                if paper is None:
                    continue
                    
                external_ids = paper.get("externalIds", {})
                open_access = paper.get("openAccessPdf")
                
                authors = []
                for author in paper.get("authors", []):
                    name = author.get("name")
                    if name:
                        authors.append(name)
                
                result = PaperResult(
                    title=paper.get("title", ""),
                    authors=authors,
                    abstract=paper.get("abstract", ""),
                    arxiv_id=external_ids.get("ArXiv"),
                    doi=external_ids.get("DOI"),
                    pdf_url=open_access.get("url") if open_access else None,
                    source="semantic_scholar",
                    citation_count=paper.get("citationCount"),
                    venue=paper.get("venue"),
                    year=paper.get("year")
                )
                results.append(result)
                
        except requests.RequestException as e:
            logger.error(f"S2 batch lookup error: {e}")
            continue
    
    logger.info(f"Found {len(results)} papers from batch lookup")
    return results


def verify_title_s2(
    title: str,
    authors: Optional[list[str]] = None,
    api_key: Optional[str] = None
) -> Optional[PaperResult]:
    """Search S2 by title to verify paper exists.
    
    Args:
        title: Paper title
        authors: Optional list of author names for verification
        api_key: Optional S2 API key
        
    Returns:
        PaperResult if found with high confidence, None otherwise
    """
    from difflib import SequenceMatcher
    
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    
    try:
        data = _rate_limited_request(
            f"{BASE_URL}/paper/search",
            params={
                "query": title,
                "limit": 3,
                "fields": "title,authors,externalIds,citationCount,year,venue"
            },
            headers=headers
        )
        
        papers = data.get("data", [])
        for paper in papers:
            paper_title = paper.get("title", "")
            similarity = SequenceMatcher(None, title.lower(), paper_title.lower()).ratio()
            
            if similarity > 0.85:
                external_ids = paper.get("externalIds", {})
                
                authors_list = []
                for author in paper.get("authors", []):
                    name = author.get("name")
                    if name:
                        authors_list.append(name)
                
                return PaperResult(
                    title=paper_title,
                    authors=authors_list,
                    abstract="",  # Not fetched in this query
                    arxiv_id=external_ids.get("ArXiv"),
                    doi=external_ids.get("DOI"),
                    source="semantic_scholar",
                    citation_count=paper.get("citationCount"),
                    venue=paper.get("venue"),
                    year=paper.get("year")
                )
        
        return None
        
    except requests.RequestException as e:
        logger.error(f"S2 title verification error: {e}")
        return None
