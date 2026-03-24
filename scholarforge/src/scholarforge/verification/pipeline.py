"""4-Layer Verification Pipeline Orchestrator."""

import json
from pathlib import Path

from ..config import VerificationConfig
from ..utils.logger import get_logger
from .arxiv_verify import verify_arxiv_id
from .crossref_verify import search_by_title_crossref, verify_doi_crossref
from .datacite_verify import verify_doi_datacite
from .models import Citation, CitationVerification, VerificationReport, VerificationResult
from .s2_verify import verify_title_s2

logger = get_logger(__name__)


def _verify_citation(
    citation: Citation,
    config: VerificationConfig,
    s2_api_key: str | None = None
) -> CitationVerification:
    """Run all verification layers for a single citation.
    
    Runs layers in order, short-circuiting on first successful verification.
    
    Args:
        citation: Citation to verify
        config: Verification configuration
        s2_api_key: Optional S2 API key
        
    Returns:
        CitationVerification with all results
    """
    results: list[VerificationResult] = []
    
    # Layer 1: arXiv ID
    if "arxiv_id" in config.layers and citation.arxiv_id:
        result = verify_arxiv_id(citation)
        results.append(result)
        if result.verified:
            logger.debug(f"Verified via arXiv: {citation.key}")
            return CitationVerification(
                citation=citation,
                results=results,
                final_verified=True,
                final_source="arxiv",
                final_confidence=result.confidence
            )
    
    # Layer 2: CrossRef DOI
    if "crossref_doi" in config.layers and citation.doi:
        result = verify_doi_crossref(citation, config.crossref_mailto)
        results.append(result)
        if result.verified:
            logger.debug(f"Verified via CrossRef: {citation.key}")
            return CitationVerification(
                citation=citation,
                results=results,
                final_verified=True,
                final_source="crossref",
                final_confidence=result.confidence
            )
    
    # Layer 3: DataCite DOI
    if "datacite_doi" in config.layers and citation.doi:
        result = verify_doi_datacite(citation)
        results.append(result)
        if result.verified:
            logger.debug(f"Verified via DataCite: {citation.key}")
            return CitationVerification(
                citation=citation,
                results=results,
                final_verified=True,
                final_source="datacite",
                final_confidence=result.confidence
            )
    
    # Layer 4: Semantic Scholar Title Match
    if "s2_title_match" in config.layers:
        result = verify_title_s2(citation, s2_api_key)
        results.append(result)
        if result.verified:
            logger.debug(f"Verified via S2: {citation.key}")
            return CitationVerification(
                citation=citation,
                results=results,
                final_verified=True,
                final_source="semantic_scholar",
                final_confidence=result.confidence
            )
    
    # All layers failed
    logger.warning(f"Could not verify: {citation.key} - {citation.title[:50]}...")
    return CitationVerification(
        citation=citation,
        results=results,
        final_verified=False,
        final_confidence=0.0
    )


def verify_all_citations(
    citations: list[Citation],
    config: VerificationConfig,
    s2_api_key: str | None = None,
    output_dir: str | None = None
) -> VerificationReport:
    """Run 4-layer verification on all citations.
    
    Args:
        citations: List of citations to verify
        config: Verification configuration
        s2_api_key: Optional S2 API key
        output_dir: Optional directory to write verification report
        
    Returns:
        VerificationReport with all results
    """
    logger.info(f"Starting verification of {len(citations)} citations")
    
    details: list[CitationVerification] = []
    verified_count = 0
    unverified_count = 0
    
    for i, citation in enumerate(citations):
        logger.debug(f"Verifying {i+1}/{len(citations)}: {citation.key}")
        
        verification = _verify_citation(citation, config, s2_api_key)
        details.append(verification)
        
        if verification.final_verified:
            verified_count += 1
        else:
            unverified_count += 1
    
    removed_count = 0
    if config.remove_unverified:
        removed_count = unverified_count
    
    report = VerificationReport(
        total=len(citations),
        verified=verified_count,
        unverified=unverified_count,
        removed=removed_count,
        details=details
    )
    
    # Write report if output directory specified
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        report_file = output_path / "verification_report.json"
        with open(report_file, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        logger.info(f"Verification report written to {report_file}")
    
    logger.info(
        f"Verification complete: {verified_count} verified, "
        f"{unverified_count} unverified, {removed_count} would be removed"
    )
    
    return report


def get_verified_citations(report: VerificationReport) -> list[Citation]:
    """Get list of verified citations from report.
    
    Args:
        report: Verification report
        
    Returns:
        List of verified citations
    """
    return [
        v.citation for v in report.details 
        if v.final_verified
    ]


def get_unverified_citations(report: VerificationReport) -> list[Citation]:
    """Get list of unverified citations from report.
    
    Args:
        report: Verification report
        
    Returns:
        List of unverified citations
    """
    return [
        v.citation for v in report.details 
        if not v.final_verified
    ]
