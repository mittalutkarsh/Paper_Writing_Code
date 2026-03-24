"""Layer 2: CrossRef DOI Verification."""

from habanero import Crossref

from ..utils.logger import get_logger
from .models import Citation, VerificationResult

logger = get_logger(__name__)


def verify_doi_crossref(citation: Citation, mailto: str = "user@example.com") -> VerificationResult:
    """Verify a citation by its DOI using CrossRef.
    
    Args:
        citation: Citation with doi
        mailto: Email for polite pool access
        
    Returns:
        VerificationResult
    """
    if not citation.doi:
        return VerificationResult(
            verified=False,
            source="crossref",
            reason="No DOI provided"
        )
    
    cr = Crossref(mailto=mailto)
    
    try:
        result = cr.works(ids=citation.doi)
        metadata = result['message']
        
        title = metadata.get('title', [None])[0]
        
        # Extract authors
        authors = []
        for author in metadata.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
        
        # Get publication date
        published = metadata.get("published-print", {}).get("date-parts", [[]])
        if not published or not published[0]:
            published = metadata.get("published-online", {}).get("date-parts", [[]])
        year = published[0][0] if published and published[0] else None
        
        return VerificationResult(
            verified=True,
            source="crossref",
            matched_title=title,
            confidence=1.0,
            metadata={
                "authors": authors,
                "container_title": metadata.get("container-title", []),
                "published_year": year,
                "type": metadata.get("type"),
                "publisher": metadata.get("publisher"),
                "volume": metadata.get("volume"),
                "issue": metadata.get("issue"),
                "page": metadata.get("page")
            }
        )
        
    except Exception as e:
        logger.warning(f"CrossRef verification failed for DOI {citation.doi}: {e}")
        return VerificationResult(
            verified=False,
            source="crossref",
            reason=f"DOI not found in CrossRef: {str(e)}"
        )


def search_by_title_crossref(
    title: str,
    mailto: str = "user@example.com"
) -> VerificationResult:
    """Search CrossRef by title as fallback.
    
    Args:
        title: Paper title
        mailto: Email for polite pool access
        
    Returns:
        VerificationResult
    """
    cr = Crossref(mailto=mailto)
    
    try:
        result = cr.works(query_bibliographic=title, limit=1)
        items = result['message']['items']
        
        if items:
            best = items[0]
            score = best.get('score', 0)
            matched_title = best['title'][0] if best.get('title') else ""
            
            # CrossRef relevance score threshold
            if score > 50:
                confidence = min(score / 100, 1.0)
                
                # Extract authors
                authors = []
                for author in best.get("author", []):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    if given and family:
                        authors.append(f"{given} {family}")
                    elif family:
                        authors.append(family)
                
                return VerificationResult(
                    verified=True,
                    source="crossref",
                    matched_title=matched_title,
                    confidence=confidence,
                    metadata={
                        "authors": authors,
                        "doi": best.get("DOI"),
                        "published_year": best.get("published-print", {}).get("date-parts", [[]])[0][0] if best.get("published-print") else None,
                        "type": best.get("type"),
                        "score": score
                    }
                )
        
        return VerificationResult(
            verified=False,
            source="crossref",
            reason="No matching title in CrossRef"
        )
        
    except Exception as e:
        logger.warning(f"CrossRef title search failed: {e}")
        return VerificationResult(
            verified=False,
            source="crossref",
            reason=f"Search error: {str(e)}"
        )
