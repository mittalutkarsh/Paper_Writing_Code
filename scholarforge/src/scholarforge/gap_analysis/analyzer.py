"""Gap Analysis — LLM-powered identification of missing information."""

from ..llm.provider import LLMProvider
from ..utils.logger import get_logger
from .models import GapItem, GapReport

logger = get_logger(__name__)


def analyze_gaps(
    topic: str,
    paper_count: int,
    knowledge_summary: str,
    llm: LLMProvider
) -> GapReport:
    """Analyze gaps in collected literature.
    
    Args:
        topic: Research topic
        paper_count: Number of papers reviewed
        knowledge_summary: Summary of extracted knowledge cards
        llm: LLM provider
        
    Returns:
        GapReport with identified gaps
    """
    logger.info(f"Analyzing gaps for topic: {topic}")
    
    system = """You are a senior AI/ML research advisor reviewing collected literature for a paper draft. Identify SPECIFIC, ACTIONABLE gaps — things the human researcher needs to provide or decide before a rigorous paper can be written.

Do NOT be vague. Instead of "more experiments may be needed", say exactly which experiment on which dataset with which baseline.

Respond ONLY in valid JSON with this schema:
{
  "missing_data": [
    {"id": "data_001", "description": "...", "priority": "required|recommended|optional", "default_suggestion": "..."}
  ],
  "methodology_decisions": [...],
  "additional_context": [...],
  "scope_refinements": [...],
  "missing_baselines": [...]
}

Priority levels:
- required: Must be filled before paper can be written
- recommended: Will significantly improve quality
- optional: Nice to have but not essential"""

    user = f"""Research Topic: {topic}

Papers Collected: {paper_count}

Knowledge Summary:
{knowledge_summary}

What specific information is still missing to write a complete, rigorous 5000+ word academic paper on this topic?

For each gap:
1. Give it a unique ID (e.g., data_001, method_001, context_001)
2. Be specific and actionable
3. Provide a default suggestion the system can use if human doesn't respond"""

    try:
        result = llm.complete_json(system, user)
        
        # Parse result into GapReport
        report = GapReport()
        
        for item_data in result.get("missing_data", []):
            report.missing_data.append(GapItem(
                id=item_data["id"],
                description=item_data["description"],
                priority=item_data["priority"],
                default_suggestion=item_data.get("default_suggestion")
            ))
        
        for item_data in result.get("methodology_decisions", []):
            report.methodology_decisions.append(GapItem(
                id=item_data["id"],
                description=item_data["description"],
                priority=item_data["priority"],
                default_suggestion=item_data.get("default_suggestion")
            ))
        
        for item_data in result.get("additional_context", []):
            report.additional_context.append(GapItem(
                id=item_data["id"],
                description=item_data["description"],
                priority=item_data["priority"],
                default_suggestion=item_data.get("default_suggestion")
            ))
        
        for item_data in result.get("scope_refinements", []):
            report.scope_refinements.append(GapItem(
                id=item_data["id"],
                description=item_data["description"],
                priority=item_data["priority"],
                default_suggestion=item_data.get("default_suggestion")
            ))
        
        for item_data in result.get("missing_baselines", []):
            report.missing_baselines.append(GapItem(
                id=item_data["id"],
                description=item_data["description"],
                priority=item_data["priority"],
                default_suggestion=item_data.get("default_suggestion")
            ))
        
        counts = report.count_by_priority()
        logger.info(
            f"Gap analysis complete: {len(report.get_all_items())} gaps identified "
            f"({counts['required']} required, {counts['recommended']} recommended, {counts['optional']} optional)"
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Gap analysis failed: {e}")
        # Return empty report
        return GapReport()
