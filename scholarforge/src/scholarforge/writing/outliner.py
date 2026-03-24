"""Paper Outline Generator."""

import yaml

from ..config import PaperConfig
from ..llm.provider import LLMProvider
from ..utils.logger import get_logger
from .models import OutlineSection, PaperOutline

logger = get_logger(__name__)


def _load_prompts() -> dict:
    """Load prompts from YAML file."""
    import os
    prompts_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts", "default.yaml")
    prompts_path = os.path.abspath(prompts_path)
    
    if os.path.exists(prompts_path):
        with open(prompts_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def generate_outline(
    topic: str,
    human_input: dict,
    citation_list: list[dict],
    knowledge_summary: str,
    config: PaperConfig,
    llm: LLMProvider
) -> PaperOutline:
    """Generate a detailed paper outline.
    
    Args:
        topic: Research topic
        human_input: Human responses from READMEMISSING.md
        citation_list: List of available citations with keys and titles
        knowledge_summary: Summary of knowledge cards
        config: Paper configuration
        llm: LLM provider
        
    Returns:
        PaperOutline with sections and word counts
    """
    logger.info(f"Generating outline for: {topic}")
    
    prompts = _load_prompts()
    outliner_prompt = prompts.get("outliner", {})
    
    system_template = outliner_prompt.get("system", """
You are a senior AI/ML researcher writing a rigorous academic paper.

Generate a detailed paper outline. Target total: {target_words} words.
Allocate word counts per section proportionally:
- Introduction: ~15% (motivate the problem, state contributions)
- Related Work: ~20% (organized by theme, not chronologically)
- Method: ~30% (precise technical description with math)
- Experiments: ~25% (setup, results, ablations)
- Conclusion: ~10% (no new information, brief future directions)

For each section, list:
- Specific key points to cover (not vague platitudes)
- Which citations to use (by BibTeX key)
- Any equations, figures, or tables needed

Respond ONLY in valid JSON.
""")
    
    # Inject global style directive (use replace to avoid KeyError on JSON examples in template)
    global_style = prompts.get("global_style_directive", "")
    system = system_template \
        .replace("{global_style_directive}", global_style) \
        .replace("{target_words}", str(config.target_words))
    
    user_template = outliner_prompt.get("user", """
Topic: {topic}
Human Input: {human_input}
Available Citations (use ONLY these BibTeX keys):
{citation_list}
Knowledge Cards Summary:
{knowledge_summary}
""")
    
    # Format citation list
    citation_str = "\n".join([
        f"- {c['key']}: {c['title']}" 
        for c in citation_list[:30]  # Limit to avoid token overflow
    ])
    
    user = user_template \
        .replace("{topic}", topic) \
        .replace("{human_input}", str(human_input)) \
        .replace("{citation_list}", citation_str) \
        .replace("{knowledge_summary}", knowledge_summary[:3000])
    
    try:
        result = llm.complete_json(system, user)
        
        # Parse sections
        sections = []
        for section_data in result.get("sections", []):
            sections.append(OutlineSection.from_dict(section_data))
        
        outline = PaperOutline(
            title=result.get("title", "Research Paper"),
            abstract=result.get("abstract", ""),
            sections=sections,
            target_words=config.target_words
        )
        
        actual_words = outline.get_total_words()
        logger.info(f"Generated outline: {len(sections)} sections, {actual_words} target words")
        
        return outline
        
    except Exception as e:
        logger.error(f"Outline generation failed: {e}")
        # Return minimal outline
        return PaperOutline(
            title="Research Paper",
            abstract="",
            sections=[
                OutlineSection(title="Introduction", target_words=int(config.target_words * 0.15)),
                OutlineSection(title="Related Work", target_words=int(config.target_words * 0.20)),
                OutlineSection(title="Method", target_words=int(config.target_words * 0.30)),
                OutlineSection(title="Experiments", target_words=int(config.target_words * 0.25)),
                OutlineSection(title="Conclusion", target_words=int(config.target_words * 0.10)),
            ],
            target_words=config.target_words
        )
