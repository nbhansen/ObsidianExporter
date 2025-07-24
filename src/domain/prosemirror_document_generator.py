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

    def __init__(self, document_mapping: Optional[Dict[str, str]] = None):
        """
        Initialize the generator with optional document mapping for wikilink resolution.
        
        Args:
            document_mapping: Map from document titles to their Outline urlIds for wikilink resolution
        """
        self.document_mapping = document_mapping or {}

    def convert_markdown(self, markdown: str) -> ProseMirrorDocument:
        """
        Convert markdown content to ProseMirror document structure.

        Args:
            markdown: Raw markdown content to convert

        Returns:
            ProseMirrorDocument with converted content
        """
        if not markdown or markdown.isspace():
            # Create a document with at least one empty paragraph
            # Outline requires at least one block node in every document
            empty_paragraph = {"type": "paragraph", "content": []}
            return ProseMirrorDocument(type="doc", content=[empty_paragraph])

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

        # Ensure at least one paragraph exists (Outline requirement)
        if not content:
            content = [{"type": "paragraph", "content": []}]

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

        # First handle wikilinks (higher priority than regular links)
        wikilink_pattern = r"\[\[([^\]|#^]+)(?:\|([^\]]+))?(?:#([^\]]+))?(?:\^([^\]]+))?\]\]"
        
        def replace_wikilink(match):
            target = match.group(1).strip()
            alias = match.group(2)
            header = match.group(3)
            block_id = match.group(4)
            
            # Use alias if provided, otherwise use target
            display_text = alias.strip() if alias else target
            
            # Create placeholder for processing
            return f"__WIKILINK__{display_text}__TARGET__{target}__END_WIKILINK__"

        # Replace wikilinks with placeholders
        processed_text = re.sub(wikilink_pattern, replace_wikilink, text)

        # Handle regular markdown links
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"

        def replace_link(match):
            link_text = match.group(1)
            href = match.group(2)
            return f"__LINK__{link_text}__HREF__{href}__END_LINK__"

        # Replace links with placeholders
        processed_text = re.sub(link_pattern, replace_link, processed_text)

        # Split by all placeholders (wikilinks first, then regular links)
        parts = re.split(r"(__WIKILINK__.*?__END_WIKILINK__|__LINK__.*?__END_LINK__)", processed_text)

        for part in parts:
            if not part:
                continue
                
            if part.startswith("__WIKILINK__"):
                # Extract wikilink components
                wikilink_match = re.match(r"__WIKILINK__(.*?)__TARGET__(.*?)__END_WIKILINK__", part)
                if wikilink_match:
                    display_text = wikilink_match.group(1)
                    target = wikilink_match.group(2)
                    
                    # Resolve wikilink to Outline document URL
                    href = self._resolve_wikilink_href(target)
                    
                    content.append({
                        "type": "text",
                        "text": display_text,
                        "marks": [{"type": "link", "attrs": {"href": href, "title": None}}],
                    })
                    
            elif part.startswith("__LINK__"):
                # Extract regular link components
                link_match = re.match(r"__LINK__(.*?)__HREF__(.*?)__END_LINK__", part)
                if link_match:
                    link_text = link_match.group(1)
                    href = link_match.group(2)
                    content.append({
                        "type": "text",
                        "text": link_text,
                        "marks": [{"type": "link", "attrs": {"href": href, "title": None}}],
                    })
                    
            else:
                # Regular text - process for bold/italic formatting
                if part:
                    content.extend(self._convert_formatted_text(part))

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

    def _resolve_wikilink_href(self, target: str) -> str:
        """
        Resolve a wikilink target to an Outline document URL.
        
        Args:
            target: The wikilink target (e.g., "Note Name" from [[Note Name]])
            
        Returns:
            href for Outline document link (e.g., "/doc/abc123def4" or fallback)
        """
        # Try direct title match first
        if target in self.document_mapping:
            url_id = self.document_mapping[target]
            return f"/doc/{url_id}"
        
        # Try case-insensitive match
        target_lower = target.lower()
        for title, url_id in self.document_mapping.items():
            if title.lower() == target_lower:
                return f"/doc/{url_id}"
        
        # Try partial matches (filename without extension)
        target_stem = target.replace(".md", "").strip()
        for title, url_id in self.document_mapping.items():
            title_stem = title.replace(".md", "").strip()
            if title_stem.lower() == target_stem.lower():
                return f"/doc/{url_id}"
        
        # If no match found, return a placeholder that won't break Outline
        # This will show as a regular link that doesn't work
        return f"#broken-link-{target.replace(' ', '-').lower()}"
