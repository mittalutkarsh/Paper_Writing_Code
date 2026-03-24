"""Tests for anti-AI-writing detection."""

import pytest
from scholarforge.writing.anti_slop import SlopDetector, rewrite_flagged


class TestSlopDetector:
    def test_detects_banned_words(self):
        detector = SlopDetector()
        
        # Text with banned words
        text = "This method plays a pivotal role in fostering innovation."
        report = detector.scan(text)
        
        assert report.total_flags > 0
        assert len(report.high_severity) > 0
        assert report.slop_score > 0

    def test_clean_text_has_no_flags(self):
        detector = SlopDetector()
        
        # Technical text without banned words
        text = "The model achieves 94.2% accuracy on the GLUE benchmark."
        report = detector.scan(text)
        
        assert report.total_flags == 0
        assert report.slop_score == 0.0

    def test_detects_dangling_ing(self):
        detector = SlopDetector()
        
        text = "The results are significant, highlighting the importance of the method."
        report = detector.scan(text)
        
        # Should flag the dangling participle
        found_dangling = any(
            f.rule == "dangling_ing" for f in report.high_severity
        )
        assert found_dangling

    def test_detects_additionally(self):
        detector = SlopDetector()
        
        text = "Additionally, the model performs well on other tasks."
        report = detector.scan(text)
        
        found = any(
            f.text.lower() == "additionally" for f in report.low_severity
        )
        assert found


class TestRewriteFlagged:
    def test_rewrites_banned_words(self):
        # This test would require an LLM, so we just check the function exists
        pass
