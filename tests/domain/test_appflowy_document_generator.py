"""
Test cases for AppFlowy document generator.

Following TDD approach - these tests define the expected behavior
for converting TransformedContent to AppFlowy JSON document format.
"""

from pathlib import Path

from src.domain.appflowy_document_generator import AppFlowyDocumentGenerator
from src.domain.models import TransformedContent


class TestAppFlowyDocumentGenerator:
    """Test suite for AppFlowyDocumentGenerator following TDD methodology."""

    def test_create_document_generator(self):
        """
        Test creating AppFlowy document generator.

        Should initialize without dependencies.
        """
        generator = AppFlowyDocumentGenerator()
        assert generator is not None

    def test_generate_simple_document(self):
        """
        Test generating simple AppFlowy document from markdown.

        Should convert basic markdown to AppFlowy JSON format.
        """
        generator = AppFlowyDocumentGenerator()

        content = TransformedContent(
            original_path=Path("test.md"),
            markdown="# Hello World\n\nThis is a simple document.",
            metadata={},
            assets=[],
            warnings=[],
        )

        result = generator.generate_document(content)

        assert "document" in result
        assert "type" in result["document"]
        assert result["document"]["type"] == "page"
        assert "children" in result["document"]

        children = result["document"]["children"]
        assert len(children) >= 2  # Heading + paragraph

        # Check heading
        heading = children[0]
        assert heading["type"] == "heading"
        assert heading["data"]["level"] == 1
        assert heading["data"]["delta"][0]["insert"] == "Hello World"

    def test_generate_document_with_metadata(self):
        """
        Test generating document with YAML frontmatter metadata.

        Should convert metadata to AppFlowy properties.
        """
        generator = AppFlowyDocumentGenerator()

        content = TransformedContent(
            original_path=Path("note.md"),
            markdown="# Note with Metadata",
            metadata={
                "title": "My Note",
                "tags": ["project", "research"],
                "created": "2024-01-01",
            },
            assets=[],
            warnings=[],
        )

        result = generator.generate_document(content)

        assert "properties" in result["document"]
        properties = result["document"]["properties"]
        assert properties["title"] == "My Note"
        assert properties["tags"] == ["project", "research"]
        assert properties["created"] == "2024-01-01"

    def test_generate_document_with_multiple_headings(self):
        """
        Test generating document with multiple heading levels.

        Should handle h1, h2, h3 etc. with correct levels.
        """
        generator = AppFlowyDocumentGenerator()

        markdown = """# Main Title
## Section 1
### Subsection
## Section 2
"""

        content = TransformedContent(
            original_path=Path("multi-heading.md"),
            markdown=markdown,
            metadata={},
            assets=[],
            warnings=[],
        )

        result = generator.generate_document(content)
        children = result["document"]["children"]

        # Find heading elements
        headings = [child for child in children if child["type"] == "heading"]
        assert len(headings) == 4

        assert headings[0]["data"]["level"] == 1
        assert headings[0]["data"]["delta"][0]["insert"] == "Main Title"

        assert headings[1]["data"]["level"] == 2
        assert headings[1]["data"]["delta"][0]["insert"] == "Section 1"

        assert headings[2]["data"]["level"] == 3
        assert headings[2]["data"]["delta"][0]["insert"] == "Subsection"

    def test_generate_document_with_lists(self):
        """
        Test generating document with bullet and numbered lists.

        Should convert markdown lists to AppFlowy list blocks.
        """
        generator = AppFlowyDocumentGenerator()

        markdown = """# Lists Example

- Item 1
- Item 2
  - Nested item

1. Numbered item 1
2. Numbered item 2
"""

        content = TransformedContent(
            original_path=Path("lists.md"),
            markdown=markdown,
            metadata={},
            assets=[],
            warnings=[],
        )

        result = generator.generate_document(content)
        children = result["document"]["children"]

        # Find list elements
        lists = [child for child in children if child["type"] == "bulleted_list"]
        assert len(lists) >= 1

    def test_generate_document_with_code_blocks(self):
        """
        Test generating document with code blocks.

        Should convert markdown code blocks to AppFlowy code blocks.
        """
        generator = AppFlowyDocumentGenerator()

        markdown = """# Code Example

```python
def hello():
    return "world"
```

Inline `code` text.
"""

        content = TransformedContent(
            original_path=Path("code.md"),
            markdown=markdown,
            metadata={},
            assets=[],
            warnings=[],
        )

        result = generator.generate_document(content)
        children = result["document"]["children"]

        # Find code block
        code_blocks = [child for child in children if child["type"] == "code"]
        assert len(code_blocks) >= 1

        code_block = code_blocks[0]
        assert "python" in code_block["data"]["language"]
        assert "def hello():" in code_block["data"]["delta"][0]["insert"]

    def test_generate_document_with_links(self):
        """
        Test generating document with transformed wikilinks.

        Should handle converted markdown links correctly.
        """
        generator = AppFlowyDocumentGenerator()

        markdown = """# Links Example

See [Other Note](other-note.md) for details.
Also check [External Link](https://example.com).
"""

        content = TransformedContent(
            original_path=Path("links.md"),
            markdown=markdown,
            metadata={},
            assets=[],
            warnings=[],
        )

        result = generator.generate_document(content)
        children = result["document"]["children"]

        # Find paragraph with links
        paragraphs = [child for child in children if child["type"] == "paragraph"]
        assert len(paragraphs) >= 1

    def test_generate_document_with_images(self):
        """
        Test generating document with image references.

        Should handle image assets and create proper references.
        """
        generator = AppFlowyDocumentGenerator()

        markdown = """# Images Example

![Sample Image](assets/sample.png)

Text with embedded image.
"""

        content = TransformedContent(
            original_path=Path("images.md"),
            markdown=markdown,
            metadata={},
            assets=[Path("assets/sample.png")],
            warnings=[],
        )

        result = generator.generate_document(content)
        children = result["document"]["children"]

        # Find image elements
        images = [child for child in children if child["type"] == "image"]
        assert len(images) >= 1

        image = images[0]
        assert "assets/sample.png" in image["data"]["url"]

    def test_generate_document_with_tables(self):
        """
        Test generating document with markdown tables.

        Should convert tables to AppFlowy table format.
        """
        generator = AppFlowyDocumentGenerator()

        markdown = """# Table Example

| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |
"""

        content = TransformedContent(
            original_path=Path("table.md"),
            markdown=markdown,
            metadata={},
            assets=[],
            warnings=[],
        )

        result = generator.generate_document(content)
        children = result["document"]["children"]

        # Find table elements
        tables = [child for child in children if child["type"] == "table"]
        assert len(tables) >= 1

    def test_convert_markdown_to_delta_format(self):
        """
        Test conversion of markdown text to AppFlowy delta format.

        Should handle bold, italic, and other formatting.
        """
        generator = AppFlowyDocumentGenerator()

        # Test bold and italic formatting
        result = generator._convert_to_delta("This is **bold** and *italic* text.")

        assert isinstance(result, list)
        assert len(result) >= 3  # "This is ", "bold", " and ", "italic", " text."

        # Find bold formatting
        bold_parts = [
            part
            for part in result
            if "attributes" in part and "bold" in part.get("attributes", {})
        ]
        assert len(bold_parts) >= 1

    def test_parse_markdown_structure(self):
        """
        Test parsing markdown into structured elements.

        Should identify headings, paragraphs, lists, etc.
        """
        generator = AppFlowyDocumentGenerator()

        markdown = """# Title
This is a paragraph.

## Subtitle
Another paragraph with **bold** text.
"""

        elements = generator._parse_markdown_structure(markdown)

        assert len(elements) >= 4  # Title, paragraph, subtitle, paragraph
        assert elements[0]["type"] == "heading"
        assert elements[0]["level"] == 1
        assert elements[0]["content"] == "Title"

    def test_handle_warnings_in_generation(self):
        """
        Test handling of warnings during document generation.

        Should preserve warnings from content transformation.
        """
        generator = AppFlowyDocumentGenerator()

        content = TransformedContent(
            original_path=Path("warning.md"),
            markdown="# Content with Issues",
            metadata={},
            assets=[],
            warnings=["Broken link detected", "Unknown callout type"],
        )

        result = generator.generate_document(content)

        # Warnings should be preserved somewhere in the result
        assert "warnings" in result or any(
            "warning" in str(v).lower() for v in result.values()
        )

    def test_generate_empty_document(self):
        """
        Test generating document from empty content.

        Should handle edge case gracefully by creating empty page.
        """
        generator = AppFlowyDocumentGenerator()

        content = TransformedContent(
            original_path=Path("empty.md"),
            markdown="",
            metadata={},
            assets=[],
            warnings=[],
        )

        result = generator.generate_document(content)

        assert "document" in result
        assert result["document"]["type"] == "page"
        assert "children" in result["document"]
        # Empty document should have one empty paragraph to preserve the note
        assert isinstance(result["document"]["children"], list)
        assert len(result["document"]["children"]) == 1
        assert result["document"]["children"][0]["type"] == "paragraph"

    def test_generate_document_with_special_characters(self):
        """
        Test generating document with unicode and special characters.

        Should handle international text and symbols correctly.
        """
        generator = AppFlowyDocumentGenerator()

        markdown = """# Special Characters Test

Text with émojis 🚀 and ünïcödé characters.
Math symbols: α, β, γ, ∑, ∆
"""

        content = TransformedContent(
            original_path=Path("special.md"),
            markdown=markdown,
            metadata={},
            assets=[],
            warnings=[],
        )

        result = generator.generate_document(content)
        children = result["document"]["children"]

        # Should preserve special characters
        assert "🚀" in str(result) or "émojis" in str(result)
