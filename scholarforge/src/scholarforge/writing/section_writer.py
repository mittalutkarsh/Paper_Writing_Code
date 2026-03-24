"""Section-by-Section Paper Drafter."""

import yaml

from ..llm.provider import LLMProvider
from ..utils.logger import get_logger
from .models import OutlineSection

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


def _count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def write_section(
    paper_title: str,
    section: OutlineSection,
    citation_list: list[dict],
    previous_sections: dict[str, str],
    human_input: dict,
    conference: str,
    llm: LLMProvider,
    max_retries: int = 2
) -> str:
    """Write a single section of the paper.
    
    Args:
        paper_title: Full paper title
        section: Section outline
        citation_list: Available citations
        previous_sections: Previously written sections for coherence
        human_input: Human responses from READMEMISSING.md
        conference: Conference format (icml2026 or iclr2026)
        llm: LLM provider
        max_retries: Maximum retries for word count adjustment
        
    Returns:
        Written section content
    """
    logger.info(f"Writing section: {section.title} (target: {section.target_words} words)")
    
    prompts = _load_prompts()
    section_writer_prompt = prompts.get("section_writer", {})
    section_guidance = prompts.get("section_guidance_templates", {})
    
    # Get section-specific guidance
    guidance = section_guidance.get(section.title, section_guidance.get("Method", ""))
    
    system_template = section_writer_prompt.get("system", """
{global_style_directive}

You are writing the "{section_title}" section of an academic paper.

ADDITIONAL RULES FOR THIS SECTION:
- Target word count: {target_words} (±10%). If you finish short, add
  technical detail — do NOT pad with significance claims.
- Use ONLY citations from the provided list. Every \\cite{{key}} must
  match a BibTeX key below. Do NOT invent citations.
- Write in LaTeX-ready format: use \\cite{{key}} for citations,
  $...$ for inline math, \\begin{{equation}}...\\end{{equation}} for
  display math, \\ref{{fig:label}} for figure references.
- CONFERENCE FORMAT: {conference}
  If ICLR: use \\citep{{key}} for parenthetical, \\citet{{key}} for textual.
  If ICML: use \\cite{{key}} for all.

SECTION-SPECIFIC GUIDANCE:
{section_guidance}
""")
    
    global_style = prompts.get("global_style_directive", "")
    
    system = system_template \
        .replace("{global_style_directive}", global_style) \
        .replace("{section_title}", section.title) \
        .replace("{target_words}", str(section.target_words)) \
        .replace("{conference}", conference) \
        .replace("{section_guidance}", guidance)
    
    user_template = section_writer_prompt.get("user", """
Paper Title: {paper_title}
Section: {section_title}
Target Words: {target_words}

Outline Key Points:
{key_points}

Available Citations (BibTeX keys and titles):
{citation_list}

Previously Written Sections (for coherence):
{previous_sections}

Human-Provided Context:
{human_input}

Write the complete "{section_title}" section now.
""")
    
    # Format key points
    key_points_str = "\n".join([f"- {p}" for p in section.key_points])
    
    # Format citations
    citation_str = "\n".join([
        f"- {c['key']}: {c['title'][:80]}..." 
        for c in citation_list[:20]
    ])
    
    # Format previous sections (brief excerpts)
    prev_str = ""
    for name, content in list(previous_sections.items())[-2:]:  # Last 2 sections
        excerpt = content[:500] + "..." if len(content) > 500 else content
        prev_str += f"\n{name}:\n{excerpt}\n"
    
    user = user_template \
        .replace("{paper_title}", paper_title) \
        .replace("{section_title}", section.title) \
        .replace("{target_words}", str(section.target_words)) \
        .replace("{key_points}", key_points_str) \
        .replace("{citation_list}", citation_str) \
        .replace("{previous_sections}", prev_str) \
        .replace("{human_input}", str(human_input))
    
    # Generate content
    content = llm.complete(system, user)
    
    # Check word count and retry if needed
    word_count = _count_words(content)
    target = section.target_words
    
    for retry in range(max_retries):
        if target * 0.9 <= word_count <= target * 1.1:
            break
        
        if word_count < target * 0.9:
            logger.warning(f"Section too short ({word_count} words), expanding...")
            expand_prompt = f"""The previous section was only {word_count} words but needs {target} words.
Expand with more technical detail, examples, or deeper explanation. Do NOT add fluff.

Previous content:
{content}

Write the expanded section:"""
            content = llm.complete(system, expand_prompt)
        elif word_count > target * 1.1:
            logger.warning(f"Section too long ({word_count} words), condensing...")
            condense_prompt = f"""The previous section was {word_count} words but should be {target} words.
Condense while keeping all key points and citations.

Previous content:
{content}

Write the condensed section:"""
            content = llm.complete(system, condense_prompt)
        
        word_count = _count_words(content)
    
    logger.info(f"Section '{section.title}' complete: {word_count} words")
    return content
