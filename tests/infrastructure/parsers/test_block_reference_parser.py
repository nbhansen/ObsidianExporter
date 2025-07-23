"""
Test cases for Obsidian block reference parser functionality.

Following TDD approach - these tests define the expected behavior
for parsing and transforming Obsidian block references to AppFlowy format.
"""

from src.infrastructure.parsers.block_reference_parser import BlockReferenceParser


class TestBlockReferenceParser:
    """Test suite for BlockReferenceParser following TDD methodology."""

    def test_extract_simple_block_reference(self):
        """
        Test extraction of simple block reference at end of line.

        Should transform 'Text ^block-id' to 'Text <!-- block: block-id -->'.
        """
        parser = BlockReferenceParser()
        content = "This is important content. ^key-point"

        expected = "This is important content. <!-- block: key-point -->"

        result = parser.transform_block_references(content)
        assert result == expected

    def test_extract_block_reference_after_paragraph(self):
        """
        Test block reference after multi-line paragraph.

        Should handle block references at end of paragraph blocks.
        """
        parser = BlockReferenceParser()
        content = """This is a multi-line paragraph
that contains important information
and ends with a block reference. ^conclusion"""

        expected = """This is a multi-line paragraph
that contains important information
and ends with a block reference. <!-- block: conclusion -->"""

        result = parser.transform_block_references(content)
        assert result == expected

    def test_extract_block_reference_after_header(self):
        """
        Test block reference after markdown header.

        Headers with block references should be transformed correctly.
        """
        parser = BlockReferenceParser()
        content = "## Important Section ^section-123"

        expected = "## Important Section <!-- block: section-123 -->"

        result = parser.transform_block_references(content)
        assert result == expected

    def test_extract_multiple_block_references(self):
        """
        Test multiple block references in same content.

        Should transform all block references independently.
        """
        parser = BlockReferenceParser()
        content = """First paragraph with reference. ^first-ref

## Header with reference ^header-ref

Another paragraph here. ^second-ref

Final content without reference."""

        expected = """First paragraph with reference. <!-- block: first-ref -->
## Header with reference <!-- block: header-ref -->
Another paragraph here. <!-- block: second-ref -->
Final content without reference."""

        result = parser.transform_block_references(content)
        assert result == expected

    def test_ignore_block_references_in_code_blocks(self):
        """
        Test that block references inside code blocks are not transformed.

        Code blocks should preserve their original content including ^block-id.
        """
        parser = BlockReferenceParser()
        content = """Regular text with reference. ^real-ref

```python
# This should not be transformed ^fake-ref
print("Code block content ^another-fake")
```

More text with reference. ^another-real"""

        expected = """Regular text with reference. <!-- block: real-ref -->
```python
# This should not be transformed ^fake-ref
print("Code block content ^another-fake")
```

More text with reference. <!-- block: another-real -->"""

        result = parser.transform_block_references(content)
        assert result == expected

    def test_ignore_block_references_in_inline_code(self):
        """
        Test that block references inside inline code are not transformed.

        Inline code with `^block-id` should remain unchanged.
        """
        parser = BlockReferenceParser()
        content = "Use syntax like `^block-id` to create references. ^real-ref"

        expected = (
            "Use syntax like `^block-id` to create references. <!-- block: real-ref -->"
        )

        result = parser.transform_block_references(content)
        assert result == expected

    def test_preserve_original_content_structure(self):
        """
        Test that original content structure is preserved.

        Line breaks, indentation, and formatting should remain intact.
        """
        parser = BlockReferenceParser()
        content = """# Main Title

This is the first paragraph with
multiple lines of content. ^para1

- List item one
- List item with reference ^list-ref
- List item three

> Blockquote content
> with multiple lines ^quote-ref

Final paragraph. ^final"""

        expected = """# Main Title

This is the first paragraph with
multiple lines of content. <!-- block: para1 -->
- List item one
- List item with reference <!-- block: list-ref -->
- List item three

> Blockquote content
> with multiple lines <!-- block: quote-ref -->
Final paragraph. <!-- block: final -->"""

        result = parser.transform_block_references(content)
        assert result == expected

    def test_handle_various_block_id_formats(self):
        """
        Test handling of different valid block ID formats.

        Should support alphanumeric, hyphens, and underscores.
        """
        parser = BlockReferenceParser()
        content = """Content with alphanumeric. ^abc123
Content with hyphens. ^block-ref-123
Content with underscores. ^block_ref_456
Content with mixed. ^mixed-ref_789"""

        expected = """Content with alphanumeric. <!-- block: abc123 -->
Content with hyphens. <!-- block: block-ref-123 -->
Content with underscores. <!-- block: block_ref_456 -->
Content with mixed. <!-- block: mixed-ref_789 -->"""

        result = parser.transform_block_references(content)
        assert result == expected

    def test_handle_whitespace_around_block_references(self):
        """
        Test handling of whitespace around block references.

        Should handle various whitespace patterns correctly.
        """
        parser = BlockReferenceParser()
        test_cases = [
            ("Content ^block-id", "Content <!-- block: block-id -->"),
            ("Content  ^block-id", "Content <!-- block: block-id -->"),
            ("Content ^block-id ", "Content <!-- block: block-id -->"),
            ("Content  ^block-id  ", "Content <!-- block: block-id -->"),
        ]

        for input_content, expected_output in test_cases:
            result = parser.transform_block_references(input_content)
            assert result == expected_output

    def test_no_transformation_without_block_references(self):
        """
        Test that content without block references remains unchanged.

        Regular markdown content should pass through unmodified.
        """
        parser = BlockReferenceParser()
        content = """# Regular Markdown

This is regular content without any block references.

- List item
- Another item

> Blockquote content

Final paragraph."""

        result = parser.transform_block_references(content)
        assert result == content  # Should be unchanged

    def test_handle_empty_content(self):
        """
        Test handling of empty or whitespace-only content.

        Should handle edge cases gracefully.
        """
        parser = BlockReferenceParser()

        # Empty string
        assert parser.transform_block_references("") == ""

        # Whitespace only
        assert parser.transform_block_references("   \n  \n  ") == "   \n  \n  "

        # Single line with just block reference
        result = parser.transform_block_references("^lonely-block")
        assert result == "<!-- block: lonely-block -->"

    def test_real_obsidian_examples(self):
        """
        Test with actual examples from Obsidian test data.

        Based on patterns found in /data/_obsidian/ test vault.
        """
        parser = BlockReferenceParser()

        # Example from real Obsidian data
        content = (
            "* The third decision concerns the **PERSISTENCE OF EMPOWERMENT**: "
            "Should empowerment happen immediately and only during system use "
            "(transient)? Or should empowerment last beyond system use "
            "(persistent)? ^f5124a\n\n"
            "* Finally, the fourth decision is whether to adopt a **participatory "
            "or expert DESIGN MINDSET**: What do we gain from taking on an "
            "expert's perspective when designing empowering technologies? ^356282"
        )

        expected = (
            "* The third decision concerns the **PERSISTENCE OF EMPOWERMENT**: "
            "Should empowerment happen immediately and only during system use "
            "(transient)? Or should empowerment last beyond system use "
            "(persistent)? <!-- block: f5124a -->\n"
            "* Finally, the fourth decision is whether to adopt a **participatory "
            "or expert DESIGN MINDSET**: What do we gain from taking on an "
            "expert's perspective when designing empowering technologies? "
            "<!-- block: 356282 -->"
        )

        result = parser.transform_block_references(content)
        assert result == expected
