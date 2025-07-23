"""
LLM configuration for Obsidian to AppFlowy exporter.

Simple configuration to enable/disable LLM features.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for LLM features."""

    enabled: bool = False
    gemini_api_key: Optional[str] = None
    model_name: str = "gemini-2.5-flash"
    min_confidence_threshold: float = 0.7
    rate_limit_per_minute: int = 60

    @classmethod
    def from_environment(cls) -> "LLMConfig":
        """Create LLM config from environment variables."""
        api_key = os.getenv("GEMINI_API_KEY")
        enabled = api_key is not None and api_key.strip() != ""

        return cls(
            enabled=enabled,
            gemini_api_key=api_key,
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            min_confidence_threshold=float(
                os.getenv("LLM_MIN_CONFIDENCE", "0.7")
            ),
            rate_limit_per_minute=int(os.getenv("LLM_RATE_LIMIT", "60")),
        )