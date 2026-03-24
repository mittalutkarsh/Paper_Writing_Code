"""Data models for paper writing."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class OutlineSection:
    """A section in the paper outline."""
    title: str
    target_words: int
    key_points: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    equations: list[str] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    subsections: list["OutlineSection"] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "target_words": self.target_words,
            "key_points": self.key_points,
            "citations": self.citations,
            "equations": self.equations,
            "figures": self.figures,
            "tables": self.tables,
            "subsections": [s.to_dict() for s in self.subsections]
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OutlineSection":
        return cls(
            title=data["title"],
            target_words=data["target_words"],
            key_points=data.get("key_points", []),
            citations=data.get("citations", []),
            equations=data.get("equations", []),
            figures=data.get("figures", []),
            tables=data.get("tables", []),
            subsections=[OutlineSection.from_dict(s) for s in data.get("subsections", [])]
        )


@dataclass
class PaperOutline:
    """Complete paper outline."""
    title: str
    abstract: str
    sections: list[OutlineSection]
    target_words: int = 5500
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "abstract": self.abstract,
            "target_words": self.target_words,
            "sections": [s.to_dict() for s in self.sections]
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperOutline":
        return cls(
            title=data["title"],
            abstract=data["abstract"],
            target_words=data.get("target_words", 5500),
            sections=[OutlineSection.from_dict(s) for s in data.get("sections", [])]
        )
    
    def get_total_words(self) -> int:
        """Get total target word count."""
        return sum(s.target_words for s in self.sections)


@dataclass
class PaperDraft:
    """Complete paper draft."""
    title: str
    abstract: str
    sections: dict[str, str]  # section_name -> content
    outline: PaperOutline
    citations: list[str]  # BibTeX keys used
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "abstract": self.abstract,
            "sections": self.sections,
            "outline": self.outline.to_dict(),
            "citations": self.citations
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperDraft":
        return cls(
            title=data.get("title", ""),
            abstract=data.get("abstract", ""),
            sections=data.get("sections", {}),
            outline=PaperOutline.from_dict(data["outline"]) if "outline" in data else PaperOutline(title="", abstract="", sections=[]),
            citations=data.get("citations", []),
        )

    def get_full_text(self) -> str:
        """Get full paper text."""
        lines = [
            f"# {self.title}",
            "",
            "## Abstract",
            "",
            self.abstract,
            ""
        ]
        
        for section_name, content in self.sections.items():
            lines.extend([
                f"## {section_name}",
                "",
                content,
                ""
            ])
        
        return "\n".join(lines)


@dataclass
class LaTeXOutput:
    """Output from LaTeX compilation."""
    tex_path: str
    bib_path: str
    pdf_path: Optional[str]
    figures_dir: str
