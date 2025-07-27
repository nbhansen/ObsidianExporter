"""
Obsidian block reference parser for transforming block references to AppFlowy format.

This parser handles standalone block references (^block-id at line endings) and
transforms them to HTML comment format for AppFlowy compatibility following
hexagonal architecture principles.
"""

import re


class BlockReferenceParser:
    """Parser for transforming Obsidian block references to AppFlowy format."""

    def __init__(self) -> None:
        """Initialize the block reference parser."""
        # Regex pattern to match block references at line endings
        # Captures: (content before ^)(block-id)(optional whitespace)
        # Handles both content+blockref and standalone blockref cases
        self._block_reference_pattern = re.compile(
            r"^(.*?)\s*\^([a-zA-Z0-9\-_]+)\s*$", re.MULTILINE
        )

        # Pattern to detect code blocks (both fenced and indented)
        self._code_block_pattern = re.compile(
            r"```[\s\S]*?```|`[^`\n]*`|^    .*$", re.MULTILINE
        )

    def transform_block_references(self, content: str) -> str:
        """
        Transform all Obsidian block references in content to AppFlowy format.

        This method processes block references by:
        1. Finding all block references at line endings
        2. Avoiding transformation within code blocks
        3. Converting ^block-id to <!-- block: block-id -->
        4. Preserving original content structure and formatting

        Args:
            content: Markdown content potentially containing block references

        Returns:
            Content with block references transformed to HTML comments
        """
        if not content or not content.strip():
            return content

        # Find all code block regions to avoid transforming within them
        code_blocks = self._find_code_block_regions(content)

        def replace_block_reference(match: re.Match[str]) -> str:
            """Replace a single block reference with HTML comment format."""
            # Check if this match is within a code block
            match_start = match.start()

            for code_start, code_end in code_blocks:
                if code_start <= match_start < code_end:
                    # This block reference is within a code block, don't transform
                    return str(match.group(0))

            line_content = match.group(1)  # Content before ^
            block_id = match.group(2)  # Block ID after ^

            # Handle edge case where line is just the block reference
            if not line_content.strip():
                return f"<!-- block: {block_id} -->"

            # Remove trailing whitespace from content and add comment
            return f"{line_content.rstrip()} <!-- block: {block_id} -->"

        # Transform all block references
        transformed = self._block_reference_pattern.sub(
            replace_block_reference, content
        )

        return transformed

    def _find_code_block_regions(self, content: str) -> list[tuple[int, int]]:
        """
        Find all code block regions in the content.

        Returns list of (start, end) positions for code blocks to avoid
        transforming block references within them.

        Args:
            content: Content to scan for code blocks

        Returns:
            List of (start_pos, end_pos) tuples for code block regions
        """
        code_regions = []

        # Find fenced code blocks (```...```)
        fenced_pattern = re.compile(r"```[\s\S]*?```", re.MULTILINE)
        for match in fenced_pattern.finditer(content):
            code_regions.append((match.start(), match.end()))

        # Find inline code (`...`)
        inline_pattern = re.compile(r"`[^`\n]*`")
        for match in inline_pattern.finditer(content):
            code_regions.append((match.start(), match.end()))

        # Find indented code blocks (4+ spaces at line start)
        indented_pattern = re.compile(r"^(    |\t).*$", re.MULTILINE)
        for match in indented_pattern.finditer(content):
            code_regions.append((match.start(), match.end()))

        return code_regions
