"""Data models for gap analysis."""

from dataclasses import dataclass, field
from typing import Any, Literal, Optional


@dataclass
class GapItem:
    """A single gap item."""
    id: str
    description: str
    priority: Literal["required", "recommended", "optional"]
    default_suggestion: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority,
            "default_suggestion": self.default_suggestion
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GapItem":
        return cls(
            id=data["id"],
            description=data["description"],
            priority=data["priority"],
            default_suggestion=data.get("default_suggestion")
        )


@dataclass
class GapReport:
    """Complete gap analysis report."""
    missing_data: list[GapItem] = field(default_factory=list)
    methodology_decisions: list[GapItem] = field(default_factory=list)
    additional_context: list[GapItem] = field(default_factory=list)
    scope_refinements: list[GapItem] = field(default_factory=list)
    missing_baselines: list[GapItem] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_data": [item.to_dict() for item in self.missing_data],
            "methodology_decisions": [item.to_dict() for item in self.methodology_decisions],
            "additional_context": [item.to_dict() for item in self.additional_context],
            "scope_refinements": [item.to_dict() for item in self.scope_refinements],
            "missing_baselines": [item.to_dict() for item in self.missing_baselines]
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GapReport":
        return cls(
            missing_data=[GapItem.from_dict(d) for d in data.get("missing_data", [])],
            methodology_decisions=[GapItem.from_dict(d) for d in data.get("methodology_decisions", [])],
            additional_context=[GapItem.from_dict(d) for d in data.get("additional_context", [])],
            scope_refinements=[GapItem.from_dict(d) for d in data.get("scope_refinements", [])],
            missing_baselines=[GapItem.from_dict(d) for d in data.get("missing_baselines", [])]
        )
    
    def get_all_items(self) -> list[GapItem]:
        """Get all gap items across all categories."""
        return (
            self.missing_data +
            self.methodology_decisions +
            self.additional_context +
            self.scope_refinements +
            self.missing_baselines
        )
    
    def get_required_items(self) -> list[GapItem]:
        """Get only required items."""
        return [item for item in self.get_all_items() if item.priority == "required"]
    
    def count_by_priority(self) -> dict[str, int]:
        """Count items by priority."""
        counts = {"required": 0, "recommended": 0, "optional": 0}
        for item in self.get_all_items():
            counts[item.priority] += 1
        return counts


@dataclass
class HumanInput:
    """Human responses to gap analysis."""
    responses: dict[str, str] = field(default_factory=dict)
    checked_items: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "responses": self.responses,
            "checked_items": self.checked_items
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HumanInput":
        return cls(
            responses=data.get("responses", {}),
            checked_items=data.get("checked_items", [])
        )
    
    def get_response(self, item_id: str) -> Optional[str]:
        """Get response for a specific item."""
        return self.responses.get(item_id)
    
    def is_checked(self, item_id: str) -> bool:
        """Check if an item is marked complete."""
        return item_id in self.checked_items
    
    def all_required_complete(self, required_ids: list[str]) -> bool:
        """Check if all required items are checked and have responses."""
        for item_id in required_ids:
            if not self.is_checked(item_id):
                return False
            if not self.get_response(item_id):
                return False
        return True
