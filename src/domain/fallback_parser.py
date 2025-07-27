"""
Fallback parser using LLM assistance for complex parsing scenarios.

This module provides intelligent fallback parsing when standard regex/AST
approaches are insufficient. It uses the LLM assistant to handle edge cases,
ambiguous syntax, and complex nested structures.
"""

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.domain.llm_assistant import (
    LLMAssistant,
    ParseAssistanceRequest,
    ParseAssistanceType,
)
from src.domain.models import ResolvedWikiLink, WikiLink


class ParsingComplexity(Enum):
    """Complexity level of content for parsing."""

    SIMPLE = "simple"
    COMPLEX = "complex"
    AMBIGUOUS = "ambiguous"


@dataclass
class FallbackCache:
    """Cache for fallback parsing results."""

    wikilink_cache: Dict[Tuple[str, str], ResolvedWikiLink]
    structure_cache: Dict[str, Dict[str, Any]]


class FallbackParser:
    """
    Fallback parser that uses LLM assistance for complex cases.

    Provides intelligent parsing for scenarios where standard approaches
    fail or have low confidence.
    """

    def __init__(
        self,
        llm_assistant: LLMAssistant,
        confidence_threshold: float = 0.7,
        enable_cache: bool = True,
    ) -> None:
        """
        Initialize fallback parser.

        Args:
            llm_assistant: LLM assistant instance
            confidence_threshold: Threshold for using fallback
            enable_cache: Whether to cache results
        """
        self.llm_assistant = llm_assistant
        self.confidence_threshold = confidence_threshold
        self.enable_cache = enable_cache
        self._cache = FallbackCache(wikilink_cache={}, structure_cache={})

    def assess_complexity(self, content: str) -> ParsingComplexity:
        """
        Assess the complexity of content for parsing.

        Args:
            content: Content to assess

        Returns:
            Complexity level
        """
        # Check for ambiguous syntax patterns
        if re.search(r"\[\[\[.*?\]\]\]", content):  # Triple brackets
            return ParsingComplexity.AMBIGUOUS

        # Check for deeply nested structures
        nesting_level = self._count_nesting_level(content)
        if nesting_level > 2:
            return ParsingComplexity.COMPLEX

        # Check for mixed complex patterns
        has_nested_callouts = bool(re.search(r">\s*>\s*\[!", content))
        has_embedded_wikilinks = bool(re.search(r">\s*.*?\[\[.*?\]\]", content))
        has_block_refs = bool(
            re.search(r"\^[a-zA-Z0-9\-_]+\s*$", content, re.MULTILINE)
        )

        complexity_factors = sum(
            [has_nested_callouts, has_embedded_wikilinks, has_block_refs]
        )
        if complexity_factors >= 2:
            return ParsingComplexity.COMPLEX

        return ParsingComplexity.SIMPLE

    def resolve_wikilink_fallback(
        self,
        wikilink: WikiLink,
        vault_files: List[Path],
        current_file: Path,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ResolvedWikiLink]:
        """
        Resolve wikilink using LLM assistance as fallback.

        Args:
            wikilink: Wikilink to resolve
            vault_files: Available files in vault
            current_file: Current file path
            context: Additional context

        Returns:
            Resolved wikilink or None if unable to resolve
        """
        if not self.llm_assistant.is_available():
            return None

        # Check cache
        cache_key = (wikilink.original, str(current_file))
        if self.enable_cache and cache_key in self._cache.wikilink_cache:
            return self._cache.wikilink_cache[cache_key]

        # Prepare LLM request
        request_context = {
            "vault_files": [str(f) for f in vault_files],
            "current_file": str(current_file),
        }
        if context:
            request_context.update(context)

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.WIKILINK_RESOLUTION,
            content=wikilink.original,
            context=request_context,
        )

        # Get LLM assistance
        response = self.llm_assistant.get_assistance(request)
        if not response:
            return None

        # Parse response and create resolved wikilink
        try:
            resolved_path = Path(response.content.strip())
            if resolved_path in vault_files:
                result = ResolvedWikiLink(
                    original=wikilink,
                    resolved_path=resolved_path,
                    is_broken=False,
                    target_exists=True,
                    resolution_method="llm_fuzzy_match",
                    confidence=response.confidence,
                )

                # Cache result
                if self.enable_cache:
                    self._cache.wikilink_cache[cache_key] = result

                return result
        except Exception:
            pass

        return None

    def parse_complex_structure(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Parse complex nested structure using LLM assistance.

        Args:
            content: Complex content to parse

        Returns:
            Parsed structure or None if unable to parse
        """
        if not self.llm_assistant.is_available():
            return None

        # Check cache
        if self.enable_cache and content in self._cache.structure_cache:
            return self._cache.structure_cache[content]

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.COMPLEX_STRUCTURE,
            content=content,
            context={"parse_type": "nested_callouts"},
        )

        response = self.llm_assistant.get_assistance(request)
        if not response:
            return None

        try:
            # Parse JSON response
            result: Dict[str, Any] = json.loads(response.content)

            # Cache result
            if self.enable_cache:
                self._cache.structure_cache[content] = result

            return result
        except json.JSONDecodeError:
            return None

    def parse_ambiguous_syntax(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Parse ambiguous syntax using LLM assistance.

        Args:
            content: Content with ambiguous syntax

        Returns:
            Parsed interpretation or None
        """
        if not self.llm_assistant.is_available():
            return None

        request = ParseAssistanceRequest(
            type=ParseAssistanceType.AMBIGUOUS_SYNTAX,
            content=content,
            context={"syntax_type": "brackets"},
        )

        response = self.llm_assistant.get_assistance(request)
        if not response:
            return None

        try:
            result: Dict[str, Any] = json.loads(response.content)
            return result
        except json.JSONDecodeError:
            # Try to parse as simple key-value
            return {"interpretation": "unknown", "content": response.content}

    def should_use_fallback(self, result: ResolvedWikiLink) -> bool:
        """
        Determine if fallback should be used based on confidence.

        Args:
            result: Result from standard parsing

        Returns:
            True if fallback should be used
        """
        if hasattr(result, "confidence"):
            return result.confidence < self.confidence_threshold

        # If no confidence, check resolution method
        low_confidence_methods = ["fuzzy_match", "partial_match"]
        return result.resolution_method in low_confidence_methods

    def resolve_wikilinks_batch_fallback(
        self,
        wikilinks: List[WikiLink],
        vault_files: List[Path],
        current_file: Path,
    ) -> List[ResolvedWikiLink]:
        """
        Resolve multiple wikilinks in batch using fallback.

        Args:
            wikilinks: List of wikilinks to resolve
            vault_files: Available files in vault
            current_file: Current file path

        Returns:
            List of resolved wikilinks
        """
        if not self.llm_assistant.is_available():
            return []

        results = []

        # For now, process individually (batch API support can be added later)
        for wikilink in wikilinks:
            result = self.resolve_wikilink_fallback(wikilink, vault_files, current_file)
            if result:
                results.append(result)

        return results

    def _count_nesting_level(self, content: str) -> int:
        """Count maximum nesting level in content."""
        max_level = 0
        for line in content.split("\n"):
            # Count leading '>' characters
            match = re.match(r"^(>\s*)+", line)
            level = (
                len(match.group(0).replace(" ", ""))
                if match
                else 0
            )
            max_level = max(max_level, level)
        return max_level
