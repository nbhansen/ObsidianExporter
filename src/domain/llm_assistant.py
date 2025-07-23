"""
LLM assistant for complex parsing scenarios.

This module provides an abstraction layer for Large Language Model (LLM)
integration to assist with complex parsing cases that standard regex/AST
approaches cannot handle reliably. It follows hexagonal architecture
principles with clean interfaces and dependency injection.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class ParseAssistanceType(Enum):
    """Types of parsing assistance that can be requested."""

    WIKILINK_RESOLUTION = "wikilink_resolution"
    COMPLEX_STRUCTURE = "complex_structure"
    AMBIGUOUS_SYNTAX = "ambiguous_syntax"


@dataclass(frozen=True)
class ParseAssistanceRequest:
    """Request for LLM parsing assistance."""

    type: ParseAssistanceType
    content: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    """Response from LLM provider."""

    content: str
    confidence: float
    reasoning: str


class LLMProvider(Protocol):
    """Protocol for LLM provider implementations."""

    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        ...

    async def generate_async(self, prompt: str) -> LLMResponse:
        """Generate response asynchronously."""
        ...

    def generate(self, prompt: str) -> LLMResponse:
        """Generate response synchronously."""
        ...


class LLMAssistant:
    """
    Main assistant class that coordinates LLM-based parsing assistance.

    Provides intelligent fallback for complex parsing scenarios while
    maintaining performance through caching and rate limiting.
    """

    def __init__(
        self,
        provider: LLMProvider,
        enable_cache: bool = True,
        rate_limit_per_minute: int = 60,
        min_confidence_threshold: float = 0.6,
    ) -> None:
        """
        Initialize LLM assistant with provider and configuration.

        Args:
            provider: LLM provider implementation
            enable_cache: Whether to cache responses
            rate_limit_per_minute: Maximum requests per minute
            min_confidence_threshold: Minimum confidence for valid responses
        """
        self.provider = provider
        self.enable_cache = enable_cache
        self.rate_limit_per_minute = rate_limit_per_minute
        self.min_confidence_threshold = min_confidence_threshold

        # Initialize cache and rate limiting
        self._cache: Dict[str, LLMResponse] = {}
        self._request_times: List[float] = []

    def is_available(self) -> bool:
        """Check if LLM assistance is available."""
        return self.provider.is_available()

    def get_assistance(self, request: ParseAssistanceRequest) -> Optional[LLMResponse]:
        """
        Get parsing assistance from LLM.

        Args:
            request: Parsing assistance request

        Returns:
            LLM response if available and confident, None otherwise
        """
        if not self.is_available():
            return None

        # Check cache
        cache_key = self._get_cache_key(request)
        if self.enable_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # Check rate limit
        if not self._check_rate_limit():
            return None

        try:
            # Format prompt based on request type
            prompt = self._format_prompt(request)

            # Get response from provider
            response = self.provider.generate(prompt)

            # Filter by confidence threshold
            if response.confidence < self.min_confidence_threshold:
                return None

            # Cache successful response
            if self.enable_cache:
                self._cache[cache_key] = response

            return response

        except Exception:
            # Graceful failure - return None
            return None

    async def get_assistance_async(
        self, request: ParseAssistanceRequest
    ) -> Optional[LLMResponse]:
        """
        Get parsing assistance from LLM asynchronously.

        Args:
            request: Parsing assistance request

        Returns:
            LLM response if available and confident, None otherwise
        """
        if not self.is_available():
            return None

        # Check cache
        cache_key = self._get_cache_key(request)
        if self.enable_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # Check rate limit
        if not self._check_rate_limit():
            return None

        try:
            # Format prompt based on request type
            prompt = self._format_prompt(request)

            # Get response from provider
            response = await self.provider.generate_async(prompt)

            # Filter by confidence threshold
            if response.confidence < self.min_confidence_threshold:
                return None

            # Cache successful response
            if self.enable_cache:
                self._cache[cache_key] = response

            return response

        except Exception:
            # Graceful failure - return None
            return None

    def _format_prompt(self, request: ParseAssistanceRequest) -> str:
        """
        Format prompt for LLM based on request type.

        Args:
            request: Parsing assistance request

        Returns:
            Formatted prompt string
        """
        if request.type == ParseAssistanceType.WIKILINK_RESOLUTION:
            return self._format_wikilink_prompt(request)
        elif request.type == ParseAssistanceType.COMPLEX_STRUCTURE:
            return self._format_structure_prompt(request)
        elif request.type == ParseAssistanceType.AMBIGUOUS_SYNTAX:
            return self._format_ambiguous_prompt(request)
        else:
            raise ValueError(f"Unknown request type: {request.type}")

    def _format_wikilink_prompt(self, request: ParseAssistanceRequest) -> str:
        """Format prompt for wikilink resolution."""
        vault_files = request.context.get("vault_files", [])
        current_file = request.context.get("current_file", "unknown")

        files_list = "\n".join(f"- {f}" for f in vault_files[:20])  # Limit to 20

        return f"""Help resolve this Obsidian wikilink to the best matching file.

Wikilink: {request.content}
Current file: {current_file}

Available files in vault:
{files_list}

Find the best match based on:
1. Filename similarity
2. Path components
3. Common abbreviations or variations

Return only the filename that best matches, with your confidence level."""

    def _format_structure_prompt(self, request: ParseAssistanceRequest) -> str:
        """Format prompt for complex structure parsing."""
        parse_type = request.context.get("parse_type", "unknown")

        return f"""Parse this complex markdown structure into a structured format.

Content:
{request.content}

Parse type: {parse_type}

Return a JSON structure representing the parsed content with proper nesting."""

    def _format_ambiguous_prompt(self, request: ParseAssistanceRequest) -> str:
        """Format prompt for ambiguous syntax interpretation."""
        syntax_type = request.context.get("syntax_type", "unknown")

        return f"""Interpret this ambiguous markdown syntax.

Content: {request.content}
Syntax type: {syntax_type}

Determine the most likely intended syntax and return the corrected version."""

    def _get_cache_key(self, request: ParseAssistanceRequest) -> str:
        """Generate cache key for request."""
        key_data = f"{request.type.value}:{request.content}:{json.dumps(request.context, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limit."""
        current_time = time.time()
        minute_ago = current_time - 60

        # Remove old request times
        self._request_times = [t for t in self._request_times if t > minute_ago]

        # Check if under limit
        if len(self._request_times) >= self.rate_limit_per_minute:
            return False

        # Record this request
        self._request_times.append(current_time)
        return True
