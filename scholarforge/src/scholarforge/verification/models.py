"""Data models for citation verification."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class VerificationResult:
    """Result of a single verification attempt."""
    verified: bool
    source: str  # which layer verified it
    matched_title: Optional[str] = None
    confidence: float = 0.0  # 0.0-1.0
    reason: Optional[str] = None  # if not verified, why
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "source": self.source,
            "matched_title": self.matched_title,
            "confidence": self.confidence,
            "reason": self.reason,
            "metadata": self.metadata
        }


@dataclass
class Citation:
    """A citation to be verified."""
    key: str  # BibTeX key
    title: str
    authors: list[str] = field(default_factory=list)
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Citation":
        return cls(
            key=data["key"],
            title=data["title"],
            authors=data.get("authors", []),
            arxiv_id=data.get("arxiv_id"),
            doi=data.get("doi"),
            year=data.get("year"),
            venue=data.get("venue"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "authors": self.authors,
            "arxiv_id": self.arxiv_id,
            "doi": self.doi,
            "year": self.year,
            "venue": self.venue
        }


@dataclass
class CitationVerification:
    """Verification result for a single citation."""
    citation: Citation
    results: list[VerificationResult] = field(default_factory=list)
    final_verified: bool = False
    final_source: Optional[str] = None
    final_confidence: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CitationVerification":
        return cls(
            citation=Citation.from_dict(data["citation"]),
            results=[VerificationResult(**r) for r in data.get("results", [])],
            final_verified=data.get("final_verified", False),
            final_source=data.get("final_source"),
            final_confidence=data.get("final_confidence", 0.0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "citation": self.citation.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "final_verified": self.final_verified,
            "final_source": self.final_source,
            "final_confidence": self.final_confidence
        }


@dataclass
class VerificationReport:
    """Complete verification report."""
    total: int
    verified: int
    unverified: int
    removed: int
    details: list[CitationVerification]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationReport":
        return cls(
            total=data.get("total", 0),
            verified=data.get("verified", 0),
            unverified=data.get("unverified", 0),
            removed=data.get("removed", 0),
            details=[CitationVerification.from_dict(d) for d in data.get("details", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "verified": self.verified,
            "unverified": self.unverified,
            "removed": self.removed,
            "details": [d.to_dict() for d in self.details]
        }
