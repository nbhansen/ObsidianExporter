"""
NotionDocumentGenerator for converting AppFlowy JSON to EXACT Notion export format.

This domain service converts AppFlowy JSON documents to the precise markdown format
that matches Notion's export specification as analyzed from AppFlowy's source code.

CRITICAL: Must generate EXACT file naming, ID format, and structure required by
AppFlowy's importer.
"""

import secrets
import urllib.parse
from typing import Any, Dict, List


class NotionDocumentGenerator:
    """
    Domain service for converting AppFlowy JSON documents to EXACT Notion format.

    Converts AppFlowy's internal JSON document structure to clean markdown
    with precise file naming, ID generation, and asset handling that matches
    Notion's export format exactly as expected by AppFlowy's web importer.
    """

    def convert_to_notion_format(
        self, appflowy_doc: Dict[str, Any], page_name: str, has_children: bool = False
    ) -> Dict[str, str]:
        """
        Convert AppFlowy JSON document to EXACT Notion format.

        Args:
            appflowy_doc: AppFlowy JSON document structure
            page_name: Human-readable page name
            has_children: Whether this page has nested content (affects path)

        Returns:
            Dictionary with exact Notion format: name, content, path

        Raises:
            ValueError: If appflowy_doc has invalid structure
        """
        if not isinstance(appflowy_doc, dict) or "document" not in appflowy_doc:
            raise ValueError("Invalid AppFlowy document structure")

        document = appflowy_doc["document"]
        if not isinstance(document, dict) or "type" not in document:
            raise ValueError("Invalid AppFlowy document structure")

        # Generate unique 32-char hex ID for this document
        notion_id = self._generate_notion_id()

        # Create exact Notion filename format
        filename = self._generate_notion_filename(page_name, notion_id)

        # Convert content to markdown
        children = document.get("children", [])
        markdown_content = self._convert_children_to_markdown(
            children, page_name, notion_id
        )

        # Determine path based on whether page has nested content
        if has_children:
            # Nested content goes in "Page Name [ID]/" directory
            path = f"{page_name} {notion_id}/"
        else:
            # Simple page uses filename as path
            path = filename

        return {"name": filename, "content": markdown_content, "path": path}

    def _generate_notion_id(self) -> str:
        """
        Generate 32-character lowercase hex ID as required by Notion format.

        CRITICAL: AppFlowy expects exactly 32-char lowercase hex, NOT UUIDs.
        Pattern validated: r"^[a-f0-9]{32}$"

        Returns:
            32-character lowercase hexadecimal string
        """
        # Generate 16 random bytes (128 bits) and convert to 32-char hex
        return secrets.token_hex(16).lower()

    def _generate_notion_filename(self, page_name: str, notion_id: str) -> str:
        """
        Generate filename in EXACT Notion format.

        CRITICAL: Must match "Page Name [32-char-hex-id].md" exactly.
        This format is validated by AppFlowy's name_and_id_from_path() function.

        Args:
            page_name: Human-readable page name
            notion_id: 32-character hex ID

        Returns:
            Filename in exact Notion format
        """
        return f"{page_name} {notion_id}.md"

    def _convert_children_to_markdown(
        self, children: List[Dict[str, Any]], page_name: str, notion_id: str
    ) -> str:
        """
        Convert list of AppFlowy children nodes to markdown.

        Args:
            children: List of AppFlowy child nodes
            page_name: Page name for asset path generation
            notion_id: Page ID for asset path generation

        Returns:
            Markdown content string
        """
        if not children:
            return ""

        markdown_lines = []

        for child in children:
            child_type = child.get("type", "")
            data = child.get("data", {})

            if child_type == "heading":
                level = data.get("level", 1)
                text = self._extract_delta_text_with_formatting(data.get("delta", []))
                markdown_lines.append("#" * level + " " + text)
                markdown_lines.append("")  # Add blank line after heading

            elif child_type == "paragraph":
                text = self._extract_delta_text_with_formatting(data.get("delta", []))
                markdown_lines.append(text)

            elif child_type == "bulleted_list":
                text = self._extract_delta_text_with_formatting(data.get("delta", []))
                markdown_lines.append("- " + text)

            elif child_type == "numbered_list":
                text = self._extract_delta_text_with_formatting(data.get("delta", []))
                markdown_lines.append("1. " + text)

            elif child_type == "code":
                text = self._extract_delta_text(data.get("delta", []))
                language = data.get("language", "")
                markdown_lines.append(f"```{language}")
                markdown_lines.append(text)
                markdown_lines.append("```")

            elif child_type == "image":
                # CRITICAL: Must use URL-encoded relative paths within same directory
                url = data.get("url", "")
                caption = data.get("caption", "")

                # Convert to Notion-style asset path with URL encoding
                notion_asset_path = self._generate_notion_asset_path(
                    url, page_name, notion_id
                )
                markdown_lines.append(f"![{caption}]({notion_asset_path})")

            elif child_type == "table":
                table_markdown = self._convert_table_to_markdown(data.get("rows", []))
                markdown_lines.append(table_markdown)

        # Join with newlines and ensure single trailing newline
        content = "\n".join(markdown_lines)
        if content and not content.endswith("\n"):
            content += "\n"

        return content

    def _generate_notion_asset_path(
        self, original_url: str, page_name: str, notion_id: str
    ) -> str:
        """
        Generate EXACT Notion asset path with URL encoding.

        CRITICAL: Must match AppFlowy's expected format exactly.
        Format: ![Image](Page%20Name%20[Page%20ID]/asset%20name.ext)

        Args:
            original_url: Original asset URL from AppFlowy
            page_name: Page name for directory
            notion_id: Page ID

        Returns:
            URL-encoded relative asset path
        """
        # Extract filename from original URL
        if "/" in original_url:
            filename = original_url.split("/")[-1]
        else:
            filename = original_url

        # Create directory name and URL-encode it
        directory_name = f"{page_name} {notion_id}"
        encoded_directory = urllib.parse.quote(directory_name)
        encoded_filename = urllib.parse.quote(filename)

        return f"{encoded_directory}/{encoded_filename}"

    def _extract_delta_text(self, delta: List[Dict[str, Any]]) -> str:
        """
        Extract plain text from AppFlowy delta operations.

        Args:
            delta: List of delta operations

        Returns:
            Plain text string
        """
        text_parts = []
        for operation in delta:
            if "insert" in operation:
                text_parts.append(str(operation["insert"]))
        return "".join(text_parts)

    def _extract_delta_text_with_formatting(self, delta: List[Dict[str, Any]]) -> str:
        """
        Extract text from delta operations preserving markdown formatting.

        Args:
            delta: List of delta operations with potential formatting

        Returns:
            Formatted markdown text string
        """
        text_parts = []
        for operation in delta:
            if "insert" in operation:
                text = str(operation["insert"])
                attributes = operation.get("attributes", {})

                if attributes.get("bold"):
                    text = f"**{text}**"
                if attributes.get("italic"):
                    text = f"*{text}*"

                text_parts.append(text)
        return "".join(text_parts)

    def _convert_table_to_markdown(self, rows: List[Dict[str, Any]]) -> str:
        """
        Convert AppFlowy table rows to markdown table format.

        Args:
            rows: List of table rows with cells

        Returns:
            Markdown table string
        """
        if not rows:
            return ""

        markdown_lines = []

        for i, row in enumerate(rows):
            cells = row.get("cells", [])
            cell_texts = []

            for cell in cells:
                cell_text = self._extract_delta_text(cell.get("delta", []))
                cell_texts.append(cell_text)

            # Create table row
            markdown_lines.append("| " + " | ".join(cell_texts) + " |")

            # Add header separator after first row
            if i == 0:
                separators = ["-" * max(10, len(text)) for text in cell_texts]
                markdown_lines.append("|" + "|".join(separators) + "|")

        return "\n".join(markdown_lines)
