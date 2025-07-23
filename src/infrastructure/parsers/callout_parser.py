"""
Obsidian callout parser for transforming callouts to AppFlowy format.

This parser handles all Obsidian callout syntax variations and transforms
them to AppFlowy-compatible markdown format with appropriate emoji prefixes
and formatting following hexagonal architecture principles.
"""

import re
from typing import Dict


class CalloutParser:
    """Parser for transforming Obsidian callouts to AppFlowy format."""

    # Comprehensive mapping of all Obsidian callout types to AppFlowy format
    CALLOUT_MAPPINGS: Dict[str, str] = {
        # Note family
        "note": "📝 **Note:**",
        # Abstract/Summary family
        "abstract": "📄 **Abstract:**",
        "summary": "📄 **Summary:**",
        "tldr": "📄 **TL;DR:**",
        # Info family
        "info": "ℹ️ **Info:**",
        # Todo family
        "todo": "✅ **Todo:**",
        # Tip family
        "tip": "💡 **Tip:**",
        "hint": "💡 **Hint:**",
        "important": "💡 **Important:**",
        # Success family
        "success": "✅ **Success:**",
        "check": "✅ **Check:**",
        "done": "✅ **Done:**",
        # Question family
        "question": "❓ **Question:**",
        "help": "❓ **Help:**",
        "faq": "❓ **FAQ:**",
        # Warning family
        "warning": "⚠️ **Warning:**",
        "caution": "⚠️ **Caution:**",
        "attention": "⚠️ **Attention:**",
        # Failure family
        "failure": "❌ **Failure:**",
        "fail": "❌ **Fail:**",
        "missing": "❌ **Missing:**",
        # Danger family
        "danger": "⚡ **Danger:**",
        "error": "⚡ **Error:**",
        # Bug family
        "bug": "🐛 **Bug:**",
        # Example family
        "example": "📋 **Example:**",
        # Quote family
        "quote": "💬 **Quote:**",
        "cite": "💬 **Cite:**",
    }

    def __init__(self) -> None:
        """Initialize the callout parser."""
        # Regex pattern to match callout headers
        # Matches: > [!type]optionalCollapsible optional custom title
        self._callout_header_pattern = re.compile(
            r"^(> )\[!(\w+)\]([+-]?)(.*)$", re.MULTILINE | re.IGNORECASE
        )

    def transform_callouts(self, content: str) -> str:
        """
        Transform all Obsidian callouts in content to AppFlowy format.

        This method processes callout blocks by:
        1. Identifying callout headers with regex
        2. Mapping callout types to AppFlowy format
        3. Preserving custom titles when provided
        4. Maintaining content structure and formatting

        Args:
            content: Markdown content potentially containing callouts

        Returns:
            Content with callouts transformed to AppFlowy format
        """

        def replace_callout_header(match) -> str:
            """Replace a single callout header with AppFlowy format."""
            blockquote_prefix = match.group(1)  # "> "
            callout_type = match.group(2).lower()  # type (case-insensitive)
            # collapsible_marker = match.group(3)  # "+", "-", or "" (unused)
            custom_title = match.group(4).strip()  # optional custom title

            # Get the AppFlowy prefix for this callout type
            appflowy_prefix = self._get_callout_prefix(callout_type, custom_title)

            # Return transformed header (strip collapsible markers)
            return f"{blockquote_prefix}{appflowy_prefix}"

        # Transform all callout headers
        transformed = self._callout_header_pattern.sub(replace_callout_header, content)

        return transformed

    def _get_callout_prefix(self, callout_type: str, custom_title: str = "") -> str:
        """
        Get the appropriate AppFlowy prefix for a callout type.

        Args:
            callout_type: The Obsidian callout type (case-insensitive)
            custom_title: Optional custom title to use instead of default

        Returns:
            AppFlowy-formatted prefix string
        """
        # Use custom title if provided
        if custom_title:
            # Determine emoji based on callout type
            base_mapping = self.CALLOUT_MAPPINGS.get(callout_type, "")
            if base_mapping:
                # Extract emoji from base mapping
                emoji = base_mapping.split(" ")[0]
                return f"{emoji} **{custom_title}:**"
            else:
                # Unknown type with custom title
                return f"**{custom_title}:**"

        # Use predefined mapping if available
        if callout_type in self.CALLOUT_MAPPINGS:
            return self.CALLOUT_MAPPINGS[callout_type]

        # Unknown callout type - use generic format
        return f"**{callout_type.title()}:**"
