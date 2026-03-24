"""Layer 1: arXiv ID Verification."""

import arxiv

from ..utils.logger import get_logger
from .models import Citation, VerificationResult

logger = get_logger(__name__)


def verify_arxiv_id(citation: Citation) -> VerificationResult:
    """Verify a citation by its arXiv ID.
    
    Args:
        citation: Citation with arxiv_id
        
    Returns:
        VerificationResult
    """
    if not citation.arxiv_id:
        return VerificationResult(
            verified=False,
            source="arxiv",
            reason="No arXiv ID provided"
        )
    
    # Clean arXiv ID (remove version suffix)
    arxiv_id = citation.arxiv_id.split('v')[0]
    
    client = arxiv.Client(delay_seconds=3.0, num_retries=3)
    
    try:
        search = arxiv.Search(id_list=[arxiv_id])
        result = next(client.results(search))
        
        # Verify title matches (fuzzy)
        from difflib import SequenceMatcher
        title_similarity = SequenceMatcher(
            None, 
            citation.title.lower(), 
            result.title.lower()
        ).ratio()
        
        if title_similarity < 0.7:
            logger.warning(
                f"arXiv ID {arxiv_id} found but title mismatch: "
                f"'{citation.title[:50]}...' vs '{result.title[:50]}...'"
            )
        
        return VerificationResult(
            verified=True,
            source="arxiv",
            matched_title=result.title,
            confidence=1.0,
            metadata={
                "authors": [a.name for a in result.authors],
                "published": result.published.isoformat() if result.published else None,
                "doi": result.doi,
                "categories": list(result.categories)
            }
        )
        
    except StopIteration:
        logger.warning(f"arXiv ID not found: {arxiv_id}")
        return VerificationResult(
            verified=False,
            source="arxiv",
            reason=f"arXiv ID {arxiv_id} not found"
        )
    except Exception as e:
        logger.error(f"arXiv verification error for {arxiv_id}: {e}")
        return VerificationResult(
            verified=False,
            source="arxiv",
            reason=f"Error: {str(e)}"
        )
