"""Layer 4: Semantic Scholar Title Match."""

from difflib import SequenceMatcher

import requests

from ..utils.logger import get_logger
from .models import Citation, VerificationResult

logger = get_logger(__name__)

BASE_URL = "https://api.semanticscholar.org/graph/v1"


def verify_title_s2(
    citation: Citation,
    api_key: str | None = None
) -> VerificationResult:
    """Verify a citation by searching Semantic Scholar by title.
    
    Last-resort verification when no DOI or arXiv ID is available.
    
    Args:
        citation: Citation to verify
        api_key: Optional S2 API key
        
    Returns:
        VerificationResult
    """
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    
    try:
        resp = requests.get(
            f"{BASE_URL}/paper/search",
            params={
                "query": citation.title,
                "limit": 3,
                "fields": "title,authors,externalIds,citationCount,year,venue"
            },
            headers=headers,
            timeout=15
        )
        resp.raise_for_status()
        
        papers = resp.json().get("data", [])
        
        for paper in papers:
            paper_title = paper.get("title", "")
            
            # Fuzzy title match
            similarity = SequenceMatcher(
                None, 
                citation.title.lower(), 
                paper_title.lower()
            ).ratio()
            
            if similarity > 0.85:
                external_ids = paper.get("externalIds", {})
                
                # Extract authors
                authors = []
                for author in paper.get("authors", []):
                    name = author.get("name")
                    if name:
                        authors.append(name)
                
                return VerificationResult(
                    verified=True,
                    source="semantic_scholar",
                    matched_title=paper_title,
                    confidence=similarity,
                    metadata={
                        "authors": authors,
                        "arxiv_id": external_ids.get("ArXiv"),
                        "doi": external_ids.get("DOI"),
                        "citation_count": paper.get("citationCount"),
                        "venue": paper.get("venue"),
                        "year": paper.get("year")
                    }
                )
        
        return VerificationResult(
            verified=False,
            source="semantic_scholar",
            reason="No title match in S2"
        )
        
    except requests.RequestException as e:
        logger.warning(f"S2 title verification failed: {e}")
        return VerificationResult(
            verified=False,
            source="semantic_scholar",
            reason=f"Request error: {str(e)}"
        )
