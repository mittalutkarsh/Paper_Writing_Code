"""Multi-Agent Peer Review System."""

import yaml

from ..llm.provider import LLMProvider
from ..utils.logger import get_logger
from ..writing.models import PaperOutline

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


def _run_reviewer(
    draft: str,
    outline: PaperOutline,
    persona: str,
    system_prompt: str,
    llm: LLMProvider
) -> dict:
    """Run a single reviewer.
    
    Args:
        draft: Paper draft text
        outline: Paper outline
        persona: Reviewer persona name
        system_prompt: System prompt for this reviewer
        llm: LLM provider
        
    Returns:
        Review dict with scores and feedback
    """
    user = f"""Paper Title: {outline.title}

Full Paper Draft:
{draft[:8000]}...

[Draft truncated for length. Review what you can see.]

Provide your review in the specified JSON format."""
    
    try:
        result = llm.complete_json(system_prompt, user)
        return result
    except Exception as e:
        logger.warning(f"Reviewer {persona} failed: {e}")
        return {
            "scores": {"novelty": 5, "soundness": 5, "clarity": 5, 
                      "significance": 5, "experiments": 5, "related_work": 5, "overall": 5},
            "strengths": [],
            "weaknesses": ["Review generation failed"],
            "ai_writing_flags": [],
            "required_revisions": [],
            "questions": []
        }


def review_paper(
    draft: str,
    outline: PaperOutline,
    llm: LLMProvider
) -> dict:
    """Run multi-agent peer review on a paper draft.
    
    Args:
        draft: Paper draft text
        outline: Paper outline
        llm: LLM provider
        
    Returns:
        Complete review report with all reviewers and meta-review
    """
    logger.info("Starting multi-agent peer review...")
    
    prompts = _load_prompts()
    peer_review_prompts = prompts.get("peer_review", {})
    
    # Run three reviewers in sequence
    reviewers = [
        ("Methodologist", peer_review_prompts.get("reviewer_a", {}).get("system", "")),
        ("Domain Expert", peer_review_prompts.get("reviewer_b", {}).get("system", "")),
        ("Clarity Editor", peer_review_prompts.get("reviewer_c", {}).get("system", ""))
    ]
    
    reviews = []
    for persona, system_prompt in reviewers:
        logger.info(f"Running reviewer: {persona}")
        review = _run_reviewer(draft, outline, persona, system_prompt, llm)
        review["persona"] = persona
        reviews.append(review)
    
    # Run meta-review
    logger.info("Running meta-review...")
    meta_system = peer_review_prompts.get("meta_review", {}).get("system", "")
    
    reviews_summary = "\n\n".join([
        f"Reviewer {i+1} ({r['persona']}):\n"
        f"Scores: {r.get('scores', {})}\n"
        f"Strengths: {r.get('strengths', [])}\n"
        f"Weaknesses: {r.get('weaknesses', [])}\n"
        f"AI Writing Flags: {r.get('ai_writing_flags', [])}"
        for i, r in enumerate(reviews)
    ])
    
    meta_user = f"""Synthesize these three reviews:

{reviews_summary}

Provide consolidated assessment in the specified JSON format."""
    
    try:
        meta_review = llm.complete_json(meta_system, meta_user)
    except Exception as e:
        logger.warning(f"Meta-review failed: {e}")
        meta_review = {
            "consolidated_scores": {},
            "decision": "Borderline",
            "required_revisions": [],
            "suggested_revisions": [],
            "ai_writing_issues": []
        }
    
    report = {
        "individual_reviews": reviews,
        "meta_review": meta_review
    }
    
    logger.info(f"Peer review complete. Decision: {meta_review.get('decision', 'Unknown')}")
    
    return report
