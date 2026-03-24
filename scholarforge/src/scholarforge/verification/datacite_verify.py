"""Layer 3: DataCite DOI Verification."""

import requests

from ..utils.logger import get_logger
from .models import Citation, VerificationResult

logger = get_logger(__name__)


def verify_doi_datacite(citation: Citation) -> VerificationResult:
    """Verify a citation by its DOI using DataCite.
    
    For DOIs not found in CrossRef (typically datasets, software, etc.)
    
    Args:
        citation: Citation with doi
        
    Returns:
        VerificationResult
    """
    if not citation.doi:
        return VerificationResult(
            verified=False,
            source="datacite",
            reason="No DOI provided"
        )
    
    try:
        resp = requests.get(
            f"https://api.datacite.org/dois/{citation.doi}",
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()['data']['attributes']
            
            titles = data.get('titles', [{}])
            title = titles[0].get('title') if titles else None
            
            # Extract creators
            creators = data.get('creators', [])
            authors = []
            for creator in creators:
                name = creator.get('name')
                if name:
                    authors.append(name)
            
            return VerificationResult(
                verified=True,
                source="datacite",
                matched_title=title,
                confidence=1.0,
                metadata={
                    "authors": authors,
                    "publisher": data.get('publisher'),
                    "publication_year": data.get('publicationYear'),
                    "resource_type": data.get('types', {}).get('resourceType'),
                    "resource_type_general": data.get('types', {}).get('resourceTypeGeneral')
                }
            )
        
        elif resp.status_code == 404:
            return VerificationResult(
                verified=False,
                source="datacite",
                reason="DOI not found in DataCite"
            )
        else:
            return VerificationResult(
                verified=False,
                source="datacite",
                reason=f"HTTP {resp.status_code}"
            )
            
    except requests.RequestException as e:
        logger.warning(f"DataCite verification failed for DOI {citation.doi}: {e}")
        return VerificationResult(
            verified=False,
            source="datacite",
            reason=f"Request error: {str(e)}"
        )
