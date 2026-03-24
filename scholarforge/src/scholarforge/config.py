"""Configuration Management for ScholarForge."""

import os
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = Field(default="openai", description="LLM provider name")
    model: str = Field(default="gpt-4o", description="Model name")
    api_key_env: str = Field(default="OPENAI_API_KEY", description="Environment variable for API key")
    base_url: Optional[str] = Field(default=None, description="Base URL for API")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)

    def get_api_key(self) -> Optional[str]:
        """Get API key from environment variable."""
        return os.environ.get(self.api_key_env)


class LiteratureConfig(BaseModel):
    """Literature search configuration."""
    max_papers: int = Field(default=30, ge=1, le=100)
    search_sources: list[str] = Field(default=["arxiv", "semantic_scholar"])
    arxiv_categories: list[str] = Field(default=["cs.AI", "cs.LG", "cs.CL", "cs.CV", "stat.ML"])
    s2_api_key_env: str = Field(default="S2_API_KEY")
    relevance_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    @field_validator('search_sources')
    @classmethod
    def validate_sources(cls, v):
        valid = {"arxiv", "semantic_scholar"}
        for source in v:
            if source not in valid:
                raise ValueError(f"Invalid search source: {source}. Must be one of {valid}")
        return v

    def get_s2_api_key(self) -> Optional[str]:
        """Get Semantic Scholar API key from environment variable."""
        return os.environ.get(self.s2_api_key_env)


class VerificationConfig(BaseModel):
    """Citation verification configuration."""
    crossref_mailto: str = Field(default="user@example.com")
    layers: list[str] = Field(default=["arxiv_id", "crossref_doi", "datacite_doi", "s2_title_match"])
    remove_unverified: bool = Field(default=True)


class PaperConfig(BaseModel):
    """Paper generation configuration."""
    target_words: int = Field(default=5500, ge=1000, le=20000)
    conference: Literal["icml2026", "iclr2026"] = Field(default="icml2026")
    sections: list[str] = Field(default=["Introduction", "Related Work", "Method", "Experiments", "Results", "Conclusion"])


class HITLConfig(BaseModel):
    """Human-in-the-loop configuration."""
    mode: Literal["cli", "file_watch", "web"] = Field(default="cli")
    auto_approve: bool = Field(default=False)
    watch_interval_sec: int = Field(default=10, ge=1)
    web_port: int = Field(default=8080, ge=1024, le=65535)
    gate_stages: list[str] = Field(default=["literature_review", "gap_analysis", "final_review"])


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    file: str = Field(default="./output/scholarforge.log")


class ProjectConfig(BaseModel):
    """Project configuration."""
    name: str = Field(default="My Research Paper")
    topic: str = Field(default="")
    output_dir: str = Field(default="./output")


class ScholarForgeConfig(BaseModel):
    """Complete ScholarForge configuration."""
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    literature: LiteratureConfig = Field(default_factory=LiteratureConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    paper: PaperConfig = Field(default_factory=PaperConfig)
    human_in_the_loop: HITLConfig = Field(default_factory=HITLConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(path: str, overrides: Optional[dict] = None) -> ScholarForgeConfig:
    """Load configuration from YAML file.
    
    Args:
        path: Path to YAML config file
        overrides: Optional dictionary of field overrides
        
    Returns:
        Validated ScholarForgeConfig instance
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    if overrides:
        data = _deep_update(data, overrides)
    
    return ScholarForgeConfig.model_validate(data)


def _deep_update(base: dict, updates: dict) -> dict:
    """Deep update a nested dictionary."""
    result = base.copy()
    for key, value in updates.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_update(result[key], value)
        else:
            result[key] = value
    return result


def create_default_config(output_path: str) -> None:
    """Create a default configuration file."""
    config = ScholarForgeConfig()
    config_dict = config.model_dump()
    
    with open(output_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
