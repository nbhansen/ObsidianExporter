"""
Test cases for NotionDocumentGenerator.

Following TDD approach - these tests define the expected behavior
for converting AppFlowy JSON documents back to clean markdown format.
"""

import pytest

from src.domain.notion_document_generator import NotionDocumentGenerator


class TestNotionDocumentGenerator:
    """Test suite for NotionDocumentGenerator following TDD methodology."""

    def test_create_notion_document_generator(self):
        """
        Test creating NotionDocumentGenerator.

        Should initialize without external dependencies.
        """
        generator = NotionDocumentGenerator()

        assert generator is not None

    def test_convert_simple_appflowy_document_to_markdown(self):
        """
        Test converting basic AppFlowy JSON document to markdown.

        Should handle simple page with heading and paragraph.
        """
        generator = NotionDocumentGenerator()

        # Given: Simple AppFlowy document
        appflowy_doc = {
            "document": {
                "type": "page",
                "children": [
                    {
                        "type": "heading",
                        "data": {"delta": [{"insert": "Test Page"}], "level": 1},
                    },
                    {
                        "type": "paragraph",
                        "data": {"delta": [{"insert": "This is a test paragraph."}]},
                    },
                ],
            }
        }

        # When: Converting to notion format
        result = generator.convert_to_notion_format(appflowy_doc, "test-page")

        # Then: Should return notion format document
        assert isinstance(result, dict)
        assert "name" in result
        assert "content" in result
        assert "path" in result
        # Name should follow Notion format: "Page Name [32-hex-id].md"
        assert result["name"].startswith("test-page ")
        assert result["name"].endswith(".md")
        assert result["content"] == "# Test Page\n\nThis is a test paragraph.\n"
        assert result["path"] == result["name"]  # Simple pages use filename as path

    def test_convert_empty_appflowy_document(self):
        """
        Test converting empty AppFlowy document to markdown.

        Should handle documents with no content gracefully.
        """
        generator = NotionDocumentGenerator()

        # Given: Empty AppFlowy document
        appflowy_doc = {"document": {"type": "page", "children": []}}

        # When: Converting to notion format
        result = generator.convert_to_notion_format(appflowy_doc, "empty")

        # Then: Should return empty notion format
        assert result["name"].startswith("empty ")
        assert result["name"].endswith(".md")
        assert result["content"] == ""
        assert result["path"] == result["name"]

    def test_convert_document_with_lists(self):
        """
        Test converting AppFlowy document with bulleted and numbered lists.

        Should preserve list formatting in markdown.
        """
        generator = NotionDocumentGenerator()

        # Given: AppFlowy document with lists
        appflowy_doc = {
            "document": {
                "type": "page",
                "children": [
                    {
                        "type": "bulleted_list",
                        "data": {"delta": [{"insert": "First bullet point"}]},
                    },
                    {
                        "type": "bulleted_list",
                        "data": {"delta": [{"insert": "Second bullet point"}]},
                    },
                    {
                        "type": "numbered_list",
                        "data": {"delta": [{"insert": "First numbered item"}]},
                    },
                ],
            }
        }

        # When: Converting to notion format
        result = generator.convert_to_notion_format(appflowy_doc, "lists")

        # Then: Should preserve list formatting
        expected_content = (
            "- First bullet point\n- Second bullet point\n1. First numbered item\n"
        )
        assert result["content"] == expected_content

    def test_convert_document_with_code_blocks(self):
        """
        Test converting AppFlowy document with code blocks.

        Should preserve code formatting and language hints.
        """
        generator = NotionDocumentGenerator()

        # Given: AppFlowy document with code block
        appflowy_doc = {
            "document": {
                "type": "page",
                "children": [
                    {
                        "type": "code",
                        "data": {
                            "delta": [{"insert": "print('Hello, World!')"}],
                            "language": "python",
                        },
                    }
                ],
            }
        }

        # When: Converting to notion format
        result = generator.convert_to_notion_format(appflowy_doc, "code")

        # Then: Should preserve code block with language
        expected_content = "```python\nprint('Hello, World!')\n```\n"
        assert result["content"] == expected_content

    def test_convert_document_with_images(self):
        """
        Test converting AppFlowy document with image references.

        Should convert to markdown image links with relative paths.
        """
        generator = NotionDocumentGenerator()

        # Given: AppFlowy document with image
        appflowy_doc = {
            "document": {
                "type": "page",
                "children": [
                    {
                        "type": "image",
                        "data": {"url": "assets/image.png", "caption": "Test image"},
                    }
                ],
            }
        }

        # When: Converting to notion format
        result = generator.convert_to_notion_format(appflowy_doc, "images")

        # Then: Should create markdown image link with Notion-style URL-encoded path
        # The content should contain the image with URL-encoded directory
        content = result["content"]
        assert content.startswith("![Test image](")
        assert content.endswith("/image.png)\n")
        # Path should be URL-encoded and contain the page name and ID
        assert "images" in content  # Should contain part of the page name

    def test_convert_document_with_tables(self):
        """
        Test converting AppFlowy document with tables.

        Should convert to markdown table format.
        """
        generator = NotionDocumentGenerator()

        # Given: AppFlowy document with table
        appflowy_doc = {
            "document": {
                "type": "page",
                "children": [
                    {
                        "type": "table",
                        "data": {
                            "rows": [
                                {
                                    "cells": [
                                        {"delta": [{"insert": "Header 1"}]},
                                        {"delta": [{"insert": "Header 2"}]},
                                    ]
                                },
                                {
                                    "cells": [
                                        {"delta": [{"insert": "Cell 1"}]},
                                        {"delta": [{"insert": "Cell 2"}]},
                                    ]
                                },
                            ]
                        },
                    }
                ],
            }
        }

        # When: Converting to notion format
        result = generator.convert_to_notion_format(appflowy_doc, "table")

        # Then: Should create markdown table
        expected_content = (
            "| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1 | Cell 2 |\n"
        )
        assert result["content"] == expected_content

    def test_handle_invalid_appflowy_document(self):
        """
        Test handling invalid AppFlowy document structure.

        Should raise appropriate error for malformed input.
        """
        generator = NotionDocumentGenerator()

        # Given: Invalid AppFlowy document
        invalid_doc = {"invalid": "structure"}

        # When/Then: Should raise ValueError
        with pytest.raises(ValueError, match="Invalid AppFlowy document structure"):
            generator.convert_to_notion_format(invalid_doc, "invalid")

    def test_preserve_rich_formatting_in_delta(self):
        """
        Test preserving rich text formatting from delta operations.

        Should convert bold, italic, and other formatting to markdown.
        """
        generator = NotionDocumentGenerator()

        # Given: AppFlowy document with rich formatting
        appflowy_doc = {
            "document": {
                "type": "page",
                "children": [
                    {
                        "type": "paragraph",
                        "data": {
                            "delta": [
                                {"insert": "This is "},
                                {"insert": "bold", "attributes": {"bold": True}},
                                {"insert": " and "},
                                {"insert": "italic", "attributes": {"italic": True}},
                                {"insert": " text."},
                            ]
                        },
                    }
                ],
            }
        }

        # When: Converting to notion format
        result = generator.convert_to_notion_format(appflowy_doc, "formatting")

        # Then: Should preserve markdown formatting
        expected_content = "This is **bold** and *italic* text.\n"
        assert result["content"] == expected_content
