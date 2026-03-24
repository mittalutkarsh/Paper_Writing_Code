"""Data models for literature search."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class PaperResult:
    """Result from a literature search."""
    title: str
    authors: list[str]
    abstract: str
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    pdf_url: Optional[str] = None
    published_date: Optional[datetime] = None
    source: str = "unknown"
    categories: list[str] = field(default_factory=list)
    citation_count: Optional[int] = None
    venue: Optional[str] = None
    year: Optional[int] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "arxiv_id": self.arxiv_id,
            "doi": self.doi,
            "pdf_url": self.pdf_url,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "source": self.source,
            "categories": self.categories,
            "citation_count": self.citation_count,
            "venue": self.venue,
            "year": self.year,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperResult":
        """Create from dictionary."""
        published = data.get("published_date")
        if published:
            published = datetime.fromisoformat(published)
        
        return cls(
            title=data["title"],
            authors=data["authors"],
            abstract=data["abstract"],
            arxiv_id=data.get("arxiv_id"),
            doi=data.get("doi"),
            pdf_url=data.get("pdf_url"),
            published_date=published,
            source=data.get("source", "unknown"),
            categories=data.get("categories", []),
            citation_count=data.get("citation_count"),
            venue=data.get("venue"),
            year=data.get("year"),
        )
    
    def get_id(self) -> str:
        """Get a unique identifier for deduplication."""
        if self.arxiv_id:
            return f"arxiv:{self.arxiv_id}"
        if self.doi:
            return f"doi:{self.doi}"
        return f"title:{self.title.lower().strip()}"


@dataclass
class KnowledgeCard:
    """Structured knowledge extracted from a paper."""
    paper: PaperResult
    key_findings: list[str] = field(default_factory=list)
    methodology: str = ""
    datasets_used: list[str] = field(default_factory=list)
    baselines_compared: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    relevance_to_topic: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "paper": self.paper.to_dict(),
            "key_findings": self.key_findings,
            "methodology": self.methodology,
            "datasets_used": self.datasets_used,
            "baselines_compared": self.baselines_compared,
            "limitations": self.limitations,
            "relevance_to_topic": self.relevance_to_topic,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeCard":
        """Create from dictionary."""
        return cls(
            paper=PaperResult.from_dict(data["paper"]),
            key_findings=data.get("key_findings", []),
            methodology=data.get("methodology", ""),
            datasets_used=data.get("datasets_used", []),
            baselines_compared=data.get("baselines_compared", []),
            limitations=data.get("limitations", []),
            relevance_to_topic=data.get("relevance_to_topic", ""),
        )
