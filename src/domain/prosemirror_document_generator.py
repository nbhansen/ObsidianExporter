"""
ProseMirrorDocumentGenerator for converting markdown to ProseMirror JSON format.

This domain service converts markdown content to ProseMirror's document structure
following the JSON schema used by Outline's import system.
"""

import re
from typing import Any, Dict, List, Optional

from .models import ProseMirrorDocument


class ProseMirrorDocumentGenerator:
    """
    Domain service for converting markdown content to ProseMirror JSON format.

    Converts standard markdown elements to ProseMirror nodes following
    the document structure expected by Outline's JSON import system.
    """

    def convert_markdown(self, markdown: str) -> ProseMirrorDocument:
        """
        Convert markdown content to ProseMirror document structure.

        Args:
            markdown: Raw markdown content to convert

        Returns:
            ProseMirrorDocument with converted content
        """
        if not markdown or markdown.isspace():
            return ProseMirrorDocument(type="doc", content=[])

        # Split markdown into blocks and process each
        blocks = self._split_into_blocks(markdown)
        content = []

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            node = self._convert_block(block)
            if node:
                content.append(node)

        return ProseMirrorDocument(type="doc", content=content)

    def _split_into_blocks(self, markdown: str) -> List[str]:
        """Split markdown into logical blocks."""
        # Handle code blocks specially to avoid splitting them
        code_blocks = []
        code_block_pattern = r"```[\s\S]*?```"

        def replace_code_block(match):
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

        # Replace code blocks with placeholders
        processed = re.sub(code_block_pattern, replace_code_block, markdown)

        # Split by double newlines first (paragraph breaks)
        initial_blocks = re.split(r"\n\s*\n", processed)

        # Further split blocks that contain different element types
        blocks = []
        for block in initial_blocks:
            # Split lines within the block
            lines = block.split("\n")
            current_block = []
            current_block_type = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Determine block type of current line
                if line.startswith("#"):
                    line_type = "heading"
                elif re.match(r"^[-*+]\s", line):
                    line_type = "list"
                elif line.startswith("```"):
                    line_type = "code"
                else:
                    line_type = "paragraph"

                # Check if we need to start a new block
                # Always start new block for headings and code blocks
                # Keep list items together
                should_start_new_block = current_block_type is not None and (
                    (
                        current_block_type != line_type
                        and not (current_block_type == "list" and line_type == "list")
                    )
                    or (line_type == "heading")  # Each heading is separate
                    or (line_type == "code")  # Each code block is separate
                )

                if should_start_new_block:
                    # Add accumulated content as a block
                    if current_block:
                        blocks.append("\n".join(current_block))
                        current_block = []

                current_block.append(line)
                current_block_type = line_type

            # Add remaining content
            if current_block:
                blocks.append("\n".join(current_block))

        # Restore code blocks
        for i, block in enumerate(blocks):
            for j, code_block in enumerate(code_blocks):
                blocks[i] = blocks[i].replace(f"__CODE_BLOCK_{j}__", code_block)

        return blocks

    def _convert_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Convert a single markdown block to ProseMirror node."""
        # Code block
        if block.startswith("```"):
            return self._convert_code_block(block)

        # Headings
        if block.startswith("#"):
            return self._convert_heading(block)

        # Lists
        if re.match(r"^[\s]*[-*+]\s", block, re.MULTILINE):
            return self._convert_list(block)

        # Regular paragraph
        return self._convert_paragraph(block)

    def _convert_heading(self, block: str) -> Dict[str, Any]:
        """Convert markdown heading to ProseMirror heading node."""
        lines = block.strip().split("\n")
        first_line = lines[0]

        # Count heading level
        level = 0
        for char in first_line:
            if char == "#":
                level += 1
            else:
                break

        # Extract heading text
        heading_text = first_line[level:].strip()
        content = self._convert_inline(heading_text)

        return {
            "type": "heading",
            "attrs": {"level": min(level, 6)},  # HTML only supports h1-h6
            "content": content,
        }

    def _convert_paragraph(self, block: str) -> Dict[str, Any]:
        """Convert markdown paragraph to ProseMirror paragraph node."""
        # Handle images in paragraphs
        content = self._convert_inline(block)

        return {"type": "paragraph", "content": content}

    def _convert_list(self, block: str) -> Dict[str, Any]:
        """Convert markdown list to ProseMirror list node."""
        lines = block.strip().split("\n")
        items = []

        for line in lines:
            line = line.strip()
            if re.match(r"^[-*+]\s", line):
                # Extract list item text
                item_text = re.sub(r"^[-*+]\s+", "", line)

                # Create list item with paragraph content
                paragraph = {
                    "type": "paragraph",
                    "content": self._convert_inline(item_text),
                }

                items.append({"type": "list_item", "content": [paragraph]})

        return {"type": "bullet_list", "content": items}

    def _convert_code_block(self, block: str) -> Dict[str, Any]:
        """Convert markdown code block to ProseMirror codeBlock node."""
        lines = block.strip().split("\n")

        # Extract language from first line
        first_line = lines[0]
        language_match = re.match(r"^```(\w+)?", first_line)
        language = (
            language_match.group(1)
            if language_match and language_match.group(1)
            else ""
        )

        # Extract code content (everything except first and last line)
        code_lines = lines[1:-1] if len(lines) > 2 else []
        code_content = "\n".join(code_lines)

        return {
            "type": "code_block",
            "attrs": {"language": language},
            "content": [{"type": "text", "text": code_content}],
        }

    def _convert_inline(self, text: str) -> List[Dict[str, Any]]:
        """Convert inline markdown to ProseMirror inline content."""
        if not text:
            return []

        # Handle images first (they're block-level in ProseMirror)
        image_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
        images = re.findall(image_pattern, text)

        if images:
            # If there are images, handle them specially
            parts = re.split(image_pattern, text)
            content = []

            i = 0
            while i < len(parts):
                if i % 3 == 0:  # Text part
                    if parts[i].strip():
                        content.extend(self._convert_text_with_formatting(parts[i]))
                elif i % 3 == 1:  # Alt text
                    alt_text = parts[i]
                    src = parts[i + 1] if i + 1 < len(parts) else ""
                    content.append(
                        {
                            "type": "image",
                            "attrs": {"src": src, "alt": alt_text, "title": None},
                        }
                    )
                    i += 1  # Skip src part
                i += 1

            return content

        return self._convert_text_with_formatting(text)

    def _convert_text_with_formatting(self, text: str) -> List[Dict[str, Any]]:
        """Convert text with formatting marks to ProseMirror text nodes."""
        if not text:
            return []

        # Simple implementation - handle basic formatting
        content = []

        # Handle links
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"

        def replace_link(match):
            link_text = match.group(1)
            href = match.group(2)
            return f"__LINK__{link_text}__HREF__{href}__END_LINK__"

        # Replace links with placeholders
        processed_text = re.sub(link_pattern, replace_link, text)

        # Split by link placeholders
        parts = re.split(r"__LINK__(.*?)__HREF__(.*?)__END_LINK__", processed_text)

        for i, part in enumerate(parts):
            if i % 3 == 0:  # Regular text
                if part:
                    content.extend(self._convert_formatted_text(part))
            elif i % 3 == 1:  # Link text
                link_text = part
                href = parts[i + 1] if i + 1 < len(parts) else ""
                content.append(
                    {
                        "type": "text",
                        "text": link_text,
                        "marks": [{"type": "link", "attrs": {"href": href}}],
                    }
                )

        return content

    def _convert_formatted_text(self, text: str) -> List[Dict[str, Any]]:
        """Convert text with bold/italic formatting."""
        if not text:
            return []

        # For now, simple implementation without complex formatting
        # This would need more sophisticated parsing for full markdown support

        # Handle bold (**text**)
        bold_pattern = r"\*\*([^*]+)\*\*"
        italic_pattern = r"\*([^*]+)\*"

        # Simple approach: if text contains formatting, create marked text
        marks = []
        clean_text = text

        if "**" in text:
            # Extract bold text (simplified)
            bold_matches = re.findall(bold_pattern, text)
            if bold_matches:
                marks.append({"type": "strong"})
                clean_text = re.sub(bold_pattern, r"\1", clean_text)

        if "*" in clean_text and "**" not in text:
            # Extract italic text (simplified)
            italic_matches = re.findall(italic_pattern, clean_text)
            if italic_matches:
                marks.append({"type": "em"})
                clean_text = re.sub(italic_pattern, r"\1", clean_text)

        node = {"type": "text", "text": clean_text}
        if marks:
            node["marks"] = marks

        return [node]
