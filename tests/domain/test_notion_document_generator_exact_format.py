"""
Test cases for NotionDocumentGenerator - EXACT Notion Format Validation.

Following CLAUDE.md TDD approach: RED → GREEN → REFACTOR
These tests validate EXACT compliance with Notion export format as analyzed
from AppFlowy source.

CRITICAL: All tests verify the precise file naming, ID format, and structure
requirements.
"""

import re

import pytest

from src.domain.notion_document_generator import NotionDocumentGenerator


class TestNotionDocumentGeneratorExactFormat:
    """Test suite validating EXACT Notion export format compliance."""

    def test_create_notion_document_generator(self):
        """
        Test creating NotionDocumentGenerator.

        Should initialize without external dependencies following hexagonal
        architecture.
        """
        generator = NotionDocumentGenerator()

        assert generator is not None

    def test_generate_notion_id_format(self):
        r"""
        Test ID generation follows EXACT Notion format.

        CRITICAL: AppFlowy expects 32-character lowercase hex IDs, NOT UUIDs.
        Pattern from AppFlowy:
        r"^(.*?)(?:\s+([a-f0-9]{32}))?(?:_[a-zA-Z0-9]+)?(?:\.[a-zA-Z0-9]+)?\s*$"
        """
        generator = NotionDocumentGenerator()

        # When: Generate Notion ID
        notion_id = generator._generate_notion_id()

        # Then: Must be 32-character lowercase hex
        assert isinstance(notion_id, str)
        assert len(notion_id) == 32
        assert notion_id.islower()
        assert re.match(r"^[a-f0-9]{32}$", notion_id), (
            f"ID '{notion_id}' must be 32-char lowercase hex"
        )

    def test_generate_notion_filename_exact_format(self):
        """
        Test filename generation follows EXACT AppFlowy naming convention.

        CRITICAL: Must match "Page Name [32-char-hex-id].md" format exactly.
        This is validated by AppFlowy's name_and_id_from_path() function.
        """
        generator = NotionDocumentGenerator()

        # Given: Page name and generated ID
        page_name = "My Test Page"
        notion_id = generator._generate_notion_id()

        # When: Generate Notion filename
        filename = generator._generate_notion_filename(page_name, notion_id)

        # Then: Must match exact format "Page Name [32-hex-id].md"
        pattern = r"^(.+) ([a-f0-9]{32})\.md$"
        match = re.match(pattern, filename)
        assert match, (
            f"Filename '{filename}' must match 'Page Name [32-hex-id].md' format"
        )

        extracted_name = match.group(1)
        extracted_id = match.group(2)

        assert extracted_name == page_name
        assert extracted_id == notion_id
        assert len(extracted_id) == 32
        assert extracted_id.islower()

    def test_convert_simple_document_to_exact_notion_format(self):
        """
        Test converting AppFlowy document to EXACT Notion format.

        CRITICAL: Output must match AppFlowy's expected structure exactly.
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
                        "data": {"delta": [{"insert": "This is test content."}]},
                    },
                ],
            }
        }

        # When: Convert to Notion format
        result = generator.convert_to_notion_format(appflowy_doc, "Test Page")

        # Then: Must return exact Notion document structure
        assert isinstance(result, dict)
        assert "name" in result
        assert "content" in result
        assert "path" in result

        # Validate filename follows exact Notion format
        filename = result["name"]
        pattern = r"^Test Page ([a-f0-9]{32})\.md$"
        assert re.match(pattern, filename), (
            f"Name '{filename}' must match Notion format"
        )

        # Validate content is clean markdown
        content = result["content"]
        expected_content = "# Test Page\n\nThis is test content.\n"
        assert content == expected_content

        # Path should match name for simple documents
        assert result["path"] == filename

    def test_asset_path_url_encoding_exact_format(self):
        """
        Test asset paths use EXACT URL encoding as expected by AppFlowy.

        CRITICAL: Spaces must become %20, paths must be relative within same directory.
        Format: ![Image Name](Page%20Name%20[Page%20ID]/Image%20Name.png)
        """
        generator = NotionDocumentGenerator()

        # Given: AppFlowy document with image
        appflowy_doc = {
            "document": {
                "type": "page",
                "children": [
                    {
                        "type": "image",
                        "data": {
                            "url": "assets/test image.png",
                            "caption": "Test Image",
                        },
                    }
                ],
            }
        }

        # When: Convert to Notion format
        result = generator.convert_to_notion_format(appflowy_doc, "My Page")

        # Then: Asset path must be URL-encoded and relative
        content = result["content"]

        # Extract the generated ID from filename for validation
        filename = result["name"]
        match = re.match(r"^My Page ([a-f0-9]{32})\.md$", filename)
        page_id = match.group(1)

        # Expected URL-encoded path format
        expected_asset_path = f"My%20Page%20{page_id}/test%20image.png"
        expected_content = f"![Test Image]({expected_asset_path})\n"

        assert content == expected_content

    def test_nested_page_directory_structure(self):
        """
        Test nested pages generate correct directory structure.

        CRITICAL: Nested content must go in "Page Name [ID]/" directories.
        """
        generator = NotionDocumentGenerator()

        # Given: Document marked as having nested content
        appflowy_doc = {
            "document": {
                "type": "page",
                "children": [
                    {
                        "type": "paragraph",
                        "data": {"delta": [{"insert": "Parent page content"}]},
                    }
                ],
            }
        }

        # When: Convert with nested flag
        result = generator.convert_to_notion_format(
            appflowy_doc, "Parent Page", has_children=True
        )

        # Then: Path should be directory, not file
        filename = result["name"]
        match = re.match(r"^Parent Page ([a-f0-9]{32})\.md$", filename)
        page_id = match.group(1)

        expected_dir_path = f"Parent Page {page_id}/"
        assert result["path"] == expected_dir_path

    def test_preserve_markdown_formatting_exactly(self):
        """
        Test rich text formatting is preserved exactly as Notion expects.

        CRITICAL: Bold, italic, etc. must be standard markdown format.
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

        # When: Convert to Notion format
        result = generator.convert_to_notion_format(appflowy_doc, "Formatted Page")

        # Then: Must preserve exact markdown formatting
        expected_content = "This is **bold** and *italic* text.\n"
        assert result["content"] == expected_content

    def test_handle_invalid_appflowy_document_structure(self):
        """
        Test error handling for invalid AppFlowy document structure.

        Should raise appropriate errors following hexagonal architecture patterns.
        """
        generator = NotionDocumentGenerator()

        # Given: Invalid document structure
        invalid_doc = {"invalid": "structure"}

        # When/Then: Should raise ValueError
        with pytest.raises(ValueError, match="Invalid AppFlowy document structure"):
            generator.convert_to_notion_format(invalid_doc, "Test Page")

    def test_empty_document_handling(self):
        """
        Test empty documents are handled gracefully.

        Should generate valid Notion format even with no content.
        """
        generator = NotionDocumentGenerator()

        # Given: Empty AppFlowy document
        empty_doc = {"document": {"type": "page", "children": []}}

        # When: Convert to Notion format
        result = generator.convert_to_notion_format(empty_doc, "Empty Page")

        # Then: Should generate valid Notion format with empty content
        filename = result["name"]
        assert re.match(r"^Empty Page ([a-f0-9]{32})\.md$", filename)
        assert result["content"] == ""
        assert result["path"] == filename

    def test_multiple_conversions_generate_unique_ids(self):
        """
        Test multiple conversions generate unique IDs.

        CRITICAL: Each conversion must generate unique 32-char hex IDs.
        """
        generator = NotionDocumentGenerator()

        # Given: Same document converted multiple times
        doc = {
            "document": {
                "type": "page",
                "children": [
                    {"type": "paragraph", "data": {"delta": [{"insert": "Test"}]}}
                ],
            }
        }

        # When: Convert multiple times
        result1 = generator.convert_to_notion_format(doc, "Test Page")
        result2 = generator.convert_to_notion_format(doc, "Test Page")

        # Then: Each should have unique ID
        id1 = re.match(r"^Test Page ([a-f0-9]{32})\.md$", result1["name"]).group(1)
        id2 = re.match(r"^Test Page ([a-f0-9]{32})\.md$", result2["name"]).group(1)

        assert id1 != id2, "Each conversion must generate unique IDs"
