"""
Test cases for ProseMirrorDocumentGenerator.

These tests validate the conversion of markdown content to ProseMirror JSON format.
"""



from src.domain.models import ProseMirrorDocument
from src.domain.prosemirror_document_generator import ProseMirrorDocumentGenerator


class TestProseMirrorDocumentGenerator:
    """Test suite for ProseMirrorDocumentGenerator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ProseMirrorDocumentGenerator()

    def test_simple_paragraph_conversion(self):
        """Test conversion of simple paragraph markdown to ProseMirror."""
        # Given: Simple paragraph markdown
        markdown = "Hello, world!"

        # When: We convert to ProseMirror
        result = self.generator.convert_markdown(markdown)

        # Then: Result should be ProseMirrorDocument with paragraph content
        assert isinstance(result, ProseMirrorDocument)
        assert result.type == "doc"
        assert len(result.content) == 1

        paragraph = result.content[0]
        assert paragraph["type"] == "paragraph"
        assert len(paragraph["content"]) == 1

        text_node = paragraph["content"][0]
        assert text_node["type"] == "text"
        assert text_node["text"] == "Hello, world!"

    def test_heading_conversion(self):
        """Test conversion of markdown headings to ProseMirror."""
        # Given: Markdown with different heading levels
        markdown = "# Heading 1\n## Heading 2\n### Heading 3"

        # When: We convert to ProseMirror
        result = self.generator.convert_markdown(markdown)

        # Then: Result should contain heading nodes with correct levels
        assert len(result.content) == 3

        h1 = result.content[0]
        assert h1["type"] == "heading"
        assert h1["attrs"]["level"] == 1
        assert h1["content"][0]["text"] == "Heading 1"

        h2 = result.content[1]
        assert h2["type"] == "heading"
        assert h2["attrs"]["level"] == 2
        assert h2["content"][0]["text"] == "Heading 2"

        h3 = result.content[2]
        assert h3["type"] == "heading"
        assert h3["attrs"]["level"] == 3
        assert h3["content"][0]["text"] == "Heading 3"

    def test_list_conversion(self):
        """Test conversion of markdown lists to ProseMirror."""
        # Given: Markdown with bullet list
        markdown = "- Item 1\n- Item 2\n- Item 3"

        # When: We convert to ProseMirror
        result = self.generator.convert_markdown(markdown)

        # Then: Result should contain bullet_list with list_item nodes
        assert len(result.content) == 1

        bullet_list = result.content[0]
        assert bullet_list["type"] == "bullet_list"
        assert len(bullet_list["content"]) == 3

        for i, item in enumerate(bullet_list["content"], 1):
            assert item["type"] == "list_item"
            paragraph = item["content"][0]
            assert paragraph["type"] == "paragraph"
            assert paragraph["content"][0]["text"] == f"Item {i}"

    def test_image_conversion(self):
        """Test conversion of markdown images to ProseMirror."""
        # Given: Markdown with image
        markdown = "![Alt text](image.png)"

        # When: We convert to ProseMirror
        result = self.generator.convert_markdown(markdown)

        # Then: Result should contain image node with proper attributes
        assert len(result.content) == 1

        paragraph = result.content[0]
        assert paragraph["type"] == "paragraph"

        image = paragraph["content"][0]
        assert image["type"] == "image"
        assert image["attrs"]["src"] == "image.png"
        assert image["attrs"]["alt"] == "Alt text"

    def test_link_conversion(self):
        """Test conversion of markdown links to ProseMirror."""
        # Given: Markdown with link
        markdown = "[Link text](https://example.com)"

        # When: We convert to ProseMirror
        result = self.generator.convert_markdown(markdown)

        # Then: Result should contain text with link mark
        paragraph = result.content[0]
        text_node = paragraph["content"][0]

        assert text_node["text"] == "Link text"
        assert "marks" in text_node
        assert len(text_node["marks"]) == 1

        link_mark = text_node["marks"][0]
        assert link_mark["type"] == "link"
        assert link_mark["attrs"]["href"] == "https://example.com"

    def test_code_block_conversion(self):
        """Test conversion of markdown code blocks to ProseMirror."""
        # Given: Markdown with code block
        markdown = "```python\nprint('Hello, world!')\n```"

        # When: We convert to ProseMirror
        result = self.generator.convert_markdown(markdown)

        # Then: Result should contain code_block node
        assert len(result.content) == 1

        code_block = result.content[0]
        assert code_block["type"] == "code_block"
        assert code_block["attrs"]["language"] == "python"
        assert code_block["content"][0]["text"] == "print('Hello, world!')"

    def test_mixed_content_conversion(self):
        """Test conversion of mixed markdown content."""
        # Given: Complex markdown with multiple elements
        markdown = """# Title

This is a paragraph with **bold** and *italic* text.

- List item 1
- List item 2

```javascript
console.log('code');
```

![Image](test.png)
"""

        # When: We convert to ProseMirror
        result = self.generator.convert_markdown(markdown)

        # Then: Result should have all elements converted properly
        assert len(result.content) == 5  # title, paragraph, list, code, image paragraph

        # Check title
        assert result.content[0]["type"] == "heading"
        assert result.content[0]["attrs"]["level"] == 1

        # Check paragraph with formatting
        paragraph = result.content[1]
        assert paragraph["type"] == "paragraph"

        # Check list
        bullet_list = result.content[2]
        assert bullet_list["type"] == "bullet_list"
        assert len(bullet_list["content"]) == 2

        # Check code block
        code_block = result.content[3]
        assert code_block["type"] == "code_block"
        assert code_block["attrs"]["language"] == "javascript"

    def test_empty_content_conversion(self):
        """Test conversion of empty markdown content."""
        # Given: Empty markdown
        markdown = ""

        # When: We convert to ProseMirror
        result = self.generator.convert_markdown(markdown)

        # Then: Result should contain one empty paragraph (Outline requirement)
        assert isinstance(result, ProseMirrorDocument)
        assert result.type == "doc"
        assert len(result.content) == 1
        assert result.content[0]["type"] == "paragraph"
        assert result.content[0]["content"] == []

    def test_whitespace_only_content(self):
        """Test conversion of whitespace-only content."""
        # Given: Whitespace-only markdown
        markdown = "   \n\n   \t  \n"

        # When: We convert to ProseMirror
        result = self.generator.convert_markdown(markdown)

        # Then: Result should contain one empty paragraph (Outline requirement)
        assert isinstance(result, ProseMirrorDocument)
        assert result.type == "doc"
        assert len(result.content) == 1
        assert result.content[0]["type"] == "paragraph"
        assert result.content[0]["content"] == []

    def test_wikilink_conversion_without_mapping(self):
        """Test wikilink conversion without document mapping creates broken links."""
        # Given: Markdown with wikilink and no document mapping
        markdown = "Check out [[Document Name]] for more info."

        # When: We convert to ProseMirror
        result = self.generator.convert_markdown(markdown)

        # Then: Result should contain link with broken link URL
        assert len(result.content) == 1
        paragraph = result.content[0]
        assert paragraph["type"] == "paragraph"
        assert len(paragraph["content"]) == 3  # text + link + text

        # Check link node
        link_node = paragraph["content"][1]
        assert link_node["type"] == "text"
        assert link_node["text"] == "Document Name"
        assert "marks" in link_node
        assert len(link_node["marks"]) == 1

        link_mark = link_node["marks"][0]
        assert link_mark["type"] == "link"
        assert link_mark["attrs"]["href"] == "#broken-link-document-name"
        assert link_mark["attrs"]["title"] is None

    def test_wikilink_conversion_with_mapping(self):
        """Test wikilink conversion with document mapping creates proper links."""
        # Given: Document mapping and markdown with wikilink
        document_mapping = {"Document Name": "abc123def4"}
        generator = ProseMirrorDocumentGenerator(document_mapping)
        markdown = "Check out [[Document Name]] for more info."

        # When: We convert to ProseMirror
        result = generator.convert_markdown(markdown)

        # Then: Result should contain proper Outline document link
        paragraph = result.content[0]
        link_node = paragraph["content"][1]
        link_mark = link_node["marks"][0]
        assert link_mark["attrs"]["href"] == "/doc/abc123def4"

    def test_wikilink_with_alias_conversion(self):
        """Test wikilink with alias conversion."""
        # Given: Document mapping and markdown with aliased wikilink
        document_mapping = {"Document Name": "abc123def4"}
        generator = ProseMirrorDocumentGenerator(document_mapping)
        markdown = "Check out [[Document Name|Display Text]] for more info."

        # When: We convert to ProseMirror
        result = generator.convert_markdown(markdown)

        # Then: Result should use alias as display text
        paragraph = result.content[0]
        link_node = paragraph["content"][1]
        assert link_node["text"] == "Display Text"
        link_mark = link_node["marks"][0]
        assert link_mark["attrs"]["href"] == "/doc/abc123def4"

    def test_wikilink_case_insensitive_matching(self):
        """Test wikilink resolution with case-insensitive matching."""
        # Given: Document mapping with different case
        document_mapping = {"Document Name": "abc123def4"}
        generator = ProseMirrorDocumentGenerator(document_mapping)
        markdown = "Check out [[document name]] for more info."

        # When: We convert to ProseMirror
        result = generator.convert_markdown(markdown)

        # Then: Should resolve despite case difference
        paragraph = result.content[0]
        link_node = paragraph["content"][1]
        link_mark = link_node["marks"][0]
        assert link_mark["attrs"]["href"] == "/doc/abc123def4"

    def test_wikilink_with_headers_and_blocks(self):
        """Test wikilink with headers and block references."""
        # Given: Document mapping and markdown with complex wikilinks
        document_mapping = {"Document Name": "abc123def4"}
        generator = ProseMirrorDocumentGenerator(document_mapping)
        markdown = "See [[Document Name#Section]] and [[Document Name^block-id]]."

        # When: We convert to ProseMirror
        result = generator.convert_markdown(markdown)

        # Then: Both should resolve to same document (header/block info ignored for now)
        paragraph = result.content[0]
        link1 = paragraph["content"][1]["marks"][0]
        link2 = paragraph["content"][3]["marks"][0]
        assert link1["attrs"]["href"] == "/doc/abc123def4"
        assert link2["attrs"]["href"] == "/doc/abc123def4"

    def test_mixed_wikilinks_and_regular_links(self):
        """Test mixing wikilinks and regular markdown links."""
        # Given: Document mapping and mixed link types
        document_mapping = {"Internal Doc": "abc123def4"}
        generator = ProseMirrorDocumentGenerator(document_mapping)
        markdown = "See [[Internal Doc]] and [External](https://example.com)."

        # When: We convert to ProseMirror
        result = generator.convert_markdown(markdown)

        # Then: Both links should be properly converted
        paragraph = result.content[0]
        internal_link = paragraph["content"][1]["marks"][0]
        external_link = paragraph["content"][3]["marks"][0]
        
        assert internal_link["attrs"]["href"] == "/doc/abc123def4"
        assert external_link["attrs"]["href"] == "https://example.com"
