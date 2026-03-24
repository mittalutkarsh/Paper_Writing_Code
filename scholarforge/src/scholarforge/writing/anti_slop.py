"""Anti-AI-Writing-Style Post-Processor.

Implements automated detection and flagging of AI-writing patterns
based on the Wikipedia "Signs of AI Writing" field guide.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from ..llm.provider import LLMProvider
from ..utils.logger import get_logger

logger = get_logger(__name__)


# AI-overused words with severity levels
HIGH_SEVERITY_WORDS = {
    'delve', 'tapestry', 'vibrant', 'testament', 'intricate', 'intricacies',
    'meticulous', 'meticulously', 'bolstered', 'garner', 'interplay', 'pivotal',
    'fostering', 'showcasing', 'underscoring', 'nestled', 'indelible mark',
    'rich tapestry', 'diverse array', 'in the heart of'
}

MEDIUM_SEVERITY_WORDS = {
    'crucial', 'landscape', 'key', 'enduring', 'enhance', 'highlighting',
    'emphasizing', 'align with', 'valuable insights', 'groundbreaking',
    'renowned', 'boasts', 'exemplifies', 'commitment to', 'natural beauty',
    'profound'
}

LOW_SEVERITY_WORDS = {
    'additionally', 'furthermore', 'moreover', 'serves as', 'stands as',
    'represents a shift', 'reflects broader'
}


@dataclass
class SlopFlag:
    """A single AI-writing pattern flag."""
    line: int
    column: int
    text: str
    context: str
    rule: str
    severity: str  # high | medium | low
    suggestion: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "line": self.line,
            "column": self.column,
            "text": self.text,
            "context": self.context,
            "rule": self.rule,
            "severity": self.severity,
            "suggestion": self.suggestion
        }


@dataclass
class SlopReport:
    """Complete slop detection report."""
    total_flags: int
    high_severity: list[SlopFlag] = field(default_factory=list)
    medium_severity: list[SlopFlag] = field(default_factory=list)
    low_severity: list[SlopFlag] = field(default_factory=list)
    slop_score: float = 0.0  # 0.0 (clean) to 1.0 (pure slop)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "total_flags": self.total_flags,
            "slop_score": self.slop_score,
            "high_severity": [f.to_dict() for f in self.high_severity],
            "medium_severity": [f.to_dict() for f in self.medium_severity],
            "low_severity": [f.to_dict() for f in self.low_severity]
        }


class SlopDetector:
    """Detector for AI-writing patterns."""
    
    def __init__(self):
        """Initialize detector with patterns."""
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> dict[str, tuple[re.Pattern, str, str]]:
        """Compile regex patterns for detection."""
        return {
            # Dangling participle analysis
            'dangling_ing': (
                re.compile(r',\s+(highlighting|underscoring|emphasizing|reflecting|symbolizing|contributing to|fostering|ensuring|showcasing|encompassing)\s+', re.IGNORECASE),
                'high',
                'Remove dangling participle phrase or integrate into sentence'
            ),
            # Significance inflation
            'significance_inflation': (
                re.compile(r'\b(marks?|represents?|shaped?|setting the stage for|key turning point|evolving landscape|focal point)\b', re.IGNORECASE),
                'medium',
                'Use specific facts instead of vague significance claims'
            ),
            # Rule of Three (flag if appears too often)
            'rule_of_three': (
                re.compile(r'\w+,\s+\w+,\s+and\s+\w+'),
                'low',
                'Avoid overusing triads for false comprehensiveness'
            ),
            # Promotional language
            'promotional': (
                re.compile(r'\b(commitment to|dedicated to|passionate about|cutting-edge|state-of-the-art)\b', re.IGNORECASE),
                'medium',
                'Remove promotional language inappropriate for academic papers'
            ),
            # Despite formula
            'despite_formula': (
                re.compile(r'Despite\s+(its|their|these)\s+[^,]+,\s+', re.IGNORECASE),
                'medium',
                'Avoid cliché setup/resolution structure'
            ),
        }
    
    def scan(self, draft: str) -> SlopReport:
        """Scan draft for AI-writing patterns.
        
        Args:
            draft: Paper draft text
            
        Returns:
            SlopReport with all flags
        """
        lines = draft.split('\n')
        high_flags = []
        medium_flags = []
        low_flags = []
        
        # Track word usage for elegant variation detection
        word_usage: dict[str, list[str]] = {}
        
        for line_num, line in enumerate(lines, 1):
            # Check for banned vocabulary
            words = re.findall(r'\b\w+\b', line.lower())
            
            for word in words:
                # High severity
                if word in HIGH_SEVERITY_WORDS:
                    col = line.lower().find(word)
                    flag = SlopFlag(
                        line=line_num,
                        column=col,
                        text=word,
                        context=line.strip()[:100],
                        rule="banned_vocabulary_high",
                        severity="high",
                        suggestion=f"Replace '{word}' with specific, concrete language"
                    )
                    high_flags.append(flag)
                
                # Medium severity
                elif word in MEDIUM_SEVERITY_WORDS:
                    col = line.lower().find(word)
                    flag = SlopFlag(
                        line=line_num,
                        column=col,
                        text=word,
                        context=line.strip()[:100],
                        rule="banned_vocabulary_medium",
                        severity="medium",
                        suggestion=f"Consider replacing '{word}' with more specific language"
                    )
                    medium_flags.append(flag)
                
                # Low severity (only flag at sentence start)
                elif word in LOW_SEVERITY_WORDS:
                    if line.strip().lower().startswith(word):
                        flag = SlopFlag(
                            line=line_num,
                            column=0,
                            text=word,
                            context=line.strip()[:100],
                            rule="banned_vocabulary_low",
                            severity="low",
                            suggestion=f"Avoid starting sentences with '{word}'"
                        )
                        low_flags.append(flag)
            
            # Check regex patterns
            for rule_name, (pattern, severity, suggestion) in self.patterns.items():
                for match in pattern.finditer(line):
                    flag = SlopFlag(
                        line=line_num,
                        column=match.start(),
                        text=match.group(),
                        context=line.strip()[:100],
                        rule=rule_name,
                        severity=severity,
                        suggestion=suggestion
                    )
                    if severity == 'high':
                        high_flags.append(flag)
                    elif severity == 'medium':
                        medium_flags.append(flag)
                    else:
                        low_flags.append(flag)
            
            # Track terms for elegant variation detection
            # (simplified: track key technical terms)
            for word in words:
                if len(word) > 5:  # Likely technical term
                    if word not in word_usage:
                        word_usage[word] = []
                    word_usage[word].append(f"line {line_num}")
        
        # Check for elegant variation (simplified)
        # In a full implementation, we'd track semantic equivalence
        
        # Calculate slop score
        total_flags = len(high_flags) + len(medium_flags) + len(low_flags)
        word_count = len(draft.split())
        
        if word_count > 0:
            # Score based on flag density and severity
            high_weight = 0.5
            medium_weight = 0.3
            low_weight = 0.1
            
            weighted_score = (
                len(high_flags) * high_weight +
                len(medium_flags) * medium_weight +
                len(low_flags) * low_weight
            ) / (word_count / 100)  # Per 100 words
            
            slop_score = min(1.0, weighted_score)
        else:
            slop_score = 0.0
        
        return SlopReport(
            total_flags=total_flags,
            high_severity=high_flags,
            medium_severity=medium_flags,
            low_severity=low_flags,
            slop_score=slop_score
        )


def rewrite_flagged(
    section: str,
    flags: list[SlopFlag],
    llm: LLMProvider
) -> str:
    """Rewrite a section to fix flagged patterns.
    
    Args:
        section: Section text
        flags: List of flags to fix
        llm: LLM provider
        
    Returns:
        Rewritten section
    """
    if not flags:
        return section
    
    # Format flags for prompt
    flags_formatted = "\n".join([
        f"- Line {f.line}: '{f.text}' - {f.suggestion}"
        for f in flags[:10]  # Limit to avoid token overflow
    ])
    
    system = """You are a copy editor fixing SPECIFIC AI-writing patterns in an academic paper. You will receive a section of text and a list of flagged issues. Fix ONLY the flagged issues. Do not rewrite anything else. Preserve all technical content, citations, and equations exactly as they are.

For each flag:
- If it's a banned word: replace with a specific, concrete alternative
- If it's a structural pattern: restructure the sentence
- If it's elegant variation: standardize to the most precise term
- If it's a vague significance claim: either delete it or replace with a specific, measurable claim

Return the corrected section. Change as little as possible."""
    
    user = f"""Section text:
{section}

Flagged issues to fix:
{flags_formatted}

Return the corrected section with ONLY the flagged issues fixed."""
    
    try:
        rewritten = llm.complete(system, user)
        return rewritten
    except Exception as e:
        logger.warning(f"Rewrite failed: {e}")
        return section
