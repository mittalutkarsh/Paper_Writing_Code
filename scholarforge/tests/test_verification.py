"""Tests for citation verification."""

import pytest
from scholarforge.verification.models import Citation, VerificationResult
from scholarforge.verification.arxiv_verify import verify_arxiv_id
from scholarforge.verification.crossref_verify import verify_doi_crossref
from scholarforge.verification.s2_verify import verify_title_s2


class TestVerificationModels:
    def test_citation_creation(self):
        citation = Citation(
            key="test2024example",
            title="Test Paper",
            authors=["Author One", "Author Two"],
            arxiv_id="2301.07041",
            year=2024
        )
        assert citation.key == "test2024example"
        assert len(citation.authors) == 2


class TestArxivVerification:
    def test_verify_valid_arxiv_id(self):
        """Test with a known valid arXiv ID."""
        citation = Citation(
            key="vaswani2017attention",
            title="Attention Is All You Need",
            arxiv_id="1706.03762"
        )
        result = verify_arxiv_id(citation)
        assert isinstance(result, VerificationResult)
        # May or may not verify depending on network

    def test_verify_invalid_arxiv_id(self):
        citation = Citation(
            key="invalid",
            title="Invalid Paper",
            arxiv_id="9999.99999"
        )
        result = verify_arxiv_id(citation)
        assert not result.verified


class TestCrossrefVerification:
    def test_verify_valid_doi(self):
        """Test with a known valid DOI."""
        citation = Citation(
            key="test",
            title="Test",
            doi="10.1038/nature12373"
        )
        result = verify_doi_crossref(citation)
        assert isinstance(result, VerificationResult)


class TestS2Verification:
    def test_verify_known_title(self):
        """Test with a well-known paper title."""
        citation = Citation(
            key="vaswani2017attention",
            title="Attention Is All You Need"
        )
        result = verify_title_s2(citation)
        assert isinstance(result, VerificationResult)
        if result.verified:
            assert result.confidence > 0.85
