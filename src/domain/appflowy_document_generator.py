"""
AppFlowy document generator for converting markdown to AppFlowy JSON format.

This domain service transforms TransformedContent into AppFlowy-compatible
JSON documents following the AppFlowy document structure specification.
"""

import re
from typing import Any, Dict, List

from .models import TransformedContent


class AppFlowyDocumentGenerator:
    """
    Domain service for generating AppFlowy JSON documents from markdown content.

    Converts TransformedContent (markdown with metadata) into AppFlowy's
    document format with proper node structure and delta text formatting.
    """

    def generate_document(self, content: TransformedContent) -> Dict[str, Any]:
        """
        Generate AppFlowy document from transformed markdown content.

        Args:
            content: TransformedContent with markdown, metadata, and assets

        Returns:
            Dict containing AppFlowy document structure
        """
        # Parse markdown into structured elements
        elements = self._parse_markdown_structure(content.markdown)

        # Convert elements to AppFlowy children
        children = []
        for element in elements:
            child = self._convert_element_to_appflowy(element)
            if child:
                children.append(child)

        # Create base document structure
        document = {"document": {"type": "page", "children": children}}

        # Add metadata as properties if present
        if content.metadata:
            document["document"]["properties"] = content.metadata.copy()

        # Preserve warnings if any
        if content.warnings:
            document["warnings"] = content.warnings.copy()

        return document

    def _parse_markdown_structure(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Parse markdown content into structured elements.

        Args:
            markdown: Raw markdown content

        Returns:
            List of structured elements with type and content
        """
        if not markdown.strip():
            # Return empty paragraph for empty files to preserve the note
            return [{"type": "paragraph", "content": ""}]

        elements = []
        lines = markdown.split("\n")
        current_element = None

        for line in lines:
            line = line.rstrip()

            # Skip empty lines between elements
            if not line and current_element:
                if current_element:
                    elements.append(current_element)
                    current_element = None
                continue
            elif not line:
                continue

            # Check for headings
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                if current_element:
                    elements.append(current_element)
                level = len(heading_match.group(1))
                content = heading_match.group(2)
                current_element = {
                    "type": "heading",
                    "level": level,
                    "content": content,
                }
                continue

            # Check for code blocks
            if line.startswith("```"):
                if current_element and current_element.get("type") == "code":
                    # End of code block
                    elements.append(current_element)
                    current_element = None
                else:
                    # Start of code block
                    if current_element:
                        elements.append(current_element)
                    language = line[3:].strip() if len(line) > 3 else ""
                    current_element = {
                        "type": "code",
                        "language": language,
                        "content": "",
                    }
                continue

            # If we're in a code block, add content
            if current_element and current_element.get("type") == "code":
                if current_element["content"]:
                    current_element["content"] += "\n"
                current_element["content"] += line
                continue

            # Check for lists
            list_match = re.match(r"^(\s*)[-*+]\s+(.+)$", line)
            if list_match:
                if current_element:
                    elements.append(current_element)
                current_element = {
                    "type": "bulleted_list",
                    "content": list_match.group(2),
                    "indent": len(list_match.group(1)),
                }
                continue

            numbered_list_match = re.match(r"^(\s*)\d+\.\s+(.+)$", line)
            if numbered_list_match:
                if current_element:
                    elements.append(current_element)
                current_element = {
                    "type": "numbered_list",
                    "content": numbered_list_match.group(2),
                    "indent": len(numbered_list_match.group(1)),
                }
                continue

            # Check for images
            image_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", line.strip())
            if image_match:
                if current_element:
                    elements.append(current_element)
                current_element = {
                    "type": "image",
                    "alt": image_match.group(1),
                    "url": image_match.group(2),
                }
                continue

            # Check for tables (markdown table format)
            if "|" in line.strip():
                # Start new table if not already in one
                if not current_element or current_element.get("type") != "table":
                    if current_element:
                        elements.append(current_element)
                    current_element = {"type": "table", "rows": []}

                # Skip separator rows (lines with only |, -, :, and spaces)
                if re.match(r"^\s*\|[\s\-:]*\|\s*$", line):
                    continue

                # Parse table row
                cells = [cell.strip() for cell in line.strip().split("|")]
                # Remove empty cells from start/end if line starts/ends with |
                if cells and not cells[0]:
                    cells = cells[1:]
                if cells and not cells[-1]:
                    cells = cells[:-1]

                if cells:  # Only add non-empty rows
                    current_element["rows"].append(cells)
                continue

            # Regular paragraph text
            if current_element and current_element.get("type") == "paragraph":
                current_element["content"] += " " + line
            else:
                if current_element:
                    elements.append(current_element)
                current_element = {"type": "paragraph", "content": line}

        # Add the last element
        if current_element:
            elements.append(current_element)

        return elements

    def _convert_element_to_appflowy(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a parsed element to AppFlowy format.

        Args:
            element: Parsed markdown element

        Returns:
            AppFlowy-formatted node or None
        """
        if element["type"] == "heading":
            return {
                "type": "heading",
                "data": {
                    "level": element["level"],
                    "delta": self._convert_to_delta(element["content"]),
                },
            }

        elif element["type"] == "paragraph":
            return {
                "type": "paragraph",
                "data": {"delta": self._convert_to_delta(element["content"])},
            }

        elif element["type"] == "code":
            return {
                "type": "code",
                "data": {
                    "language": element["language"],
                    "delta": [{"insert": element["content"]}],
                },
            }

        elif element["type"] == "bulleted_list":
            return {
                "type": "bulleted_list",
                "data": {"delta": self._convert_to_delta(element["content"])},
            }

        elif element["type"] == "numbered_list":
            return {
                "type": "numbered_list",
                "data": {"delta": self._convert_to_delta(element["content"])},
            }

        elif element["type"] == "image":
            return {
                "type": "image",
                "data": {"url": element["url"], "alt": element["alt"]},
            }

        elif element["type"] == "table":
            return {"type": "table", "data": {"rows": element["rows"]}}

        return None

    def _convert_to_delta(self, text: str) -> List[Dict[str, Any]]:
        """
        Convert markdown text to AppFlowy delta format.

        Args:
            text: Markdown-formatted text

        Returns:
            List of delta operations with formatting
        """
        if not text:
            return [{"insert": ""}]

        # Simple implementation - handle basic formatting
        delta = []
        current_pos = 0

        # Find bold patterns **text**
        for match in re.finditer(r"\*\*([^*]+)\*\*", text):
            # Add text before bold
            if match.start() > current_pos:
                delta.append({"insert": text[current_pos : match.start()]})

            # Add bold text
            delta.append({"insert": match.group(1), "attributes": {"bold": True}})
            current_pos = match.end()

        # Find italic patterns *text*
        remaining_text = text[current_pos:]
        italic_pos = 0
        for match in re.finditer(r"\*([^*]+)\*", remaining_text):
            # Add text before italic
            if match.start() > italic_pos:
                delta.append({"insert": remaining_text[italic_pos : match.start()]})

            # Add italic text
            delta.append({"insert": match.group(1), "attributes": {"italic": True}})
            italic_pos = match.end()

        # Add remaining text
        if italic_pos < len(remaining_text):
            delta.append({"insert": remaining_text[italic_pos:]})
        elif current_pos < len(text) and not delta:
            # No formatting found, add plain text
            delta.append({"insert": text})

        # Clean up empty inserts and ensure at least one element
        delta = [d for d in delta if d.get("insert")]
        if not delta:
            delta = [{"insert": text}]

        return delta
