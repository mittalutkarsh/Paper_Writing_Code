"""Tests for configuration module."""

import pytest
from scholarforge.config import (
    LLMConfig,
    LiteratureConfig,
    ScholarForgeConfig,
    load_config,
    create_default_config,
)


def test_llm_config_defaults():
    config = LLMConfig()
    assert config.provider == "openai"
    assert config.model == "gpt-4o"
    assert config.temperature == 0.3


def test_literature_config_validation():
    with pytest.raises(ValueError):
        LiteratureConfig(search_sources=["invalid_source"])


def test_create_default_config(tmp_path):
    config_path = tmp_path / "test_config.yaml"
    create_default_config(str(config_path))
    assert config_path.exists()
    
    # Should be loadable
    config = load_config(str(config_path))
    assert isinstance(config, ScholarForgeConfig)
