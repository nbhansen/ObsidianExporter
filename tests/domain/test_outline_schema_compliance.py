"""
Test compliance with Outline's ProseMirror schema.

This test suite ensures our generated ProseMirror documents use only
node types and mark types that are supported by Outline's schema.
"""

from src.domain.prosemirror_document_generator import ProseMirrorDocumentGenerator


class TestOutlineSchemaCompliance:
    """Test suite to ensure ProseMirror output complies with Outline's schema."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ProseMirrorDocumentGenerator()

    # Define Outline's supported node and mark types based on codebase analysis
    SUPPORTED_NODE_TYPES = {
        "doc",
        "paragraph",
        "heading",
        "bullet_list",
        "list_item",
        "code_block",
        "blockquote",
        "horizontal_rule",
        "image",
        "text",
    }

    SUPPORTED_MARK_TYPES = {
        "strong",
        "em",
        "code_inline",
        "strikethrough",
        "underline",
        "highlight",
        "link",
        "comment",
        "placeholder",
    }

    def test_node_types_compliance(self):
        """Test that all generated node types are supported by Outline."""
        # Test various markdown content that generates different node types
        test_cases = [
            "# Heading 1",
            "## Heading 2",
            "Regular paragraph",
            "- List item 1\n- List item 2",
            "```python\nprint('hello')\n```",
            "![alt text](image.png)",
            "> Blockquote text",
            "---",  # horizontal rule
        ]

        for markdown in test_cases:
            result = self.generator.convert_markdown(markdown)
            self._validate_node_types(result.content, f"Input: {markdown}")

    def test_mark_types_compliance(self):
        """Test that all generated mark types are supported by Outline."""
        # Test various markdown content that generates different mark types
        test_cases = [
            "**bold text**",
            "*italic text*",
            "[link text](https://example.com)",
            "~~strikethrough~~",  # if supported
            "`inline code`",  # if supported
        ]

        for markdown in test_cases:
            result = self.generator.convert_markdown(markdown)
            self._validate_mark_types(result.content, f"Input: {markdown}")

    def test_specific_mark_names(self):
        """Test that specific mark names match Outline's schema exactly."""
        # Test bold
        result = self.generator.convert_markdown("**bold text**")
        bold_marks = self._extract_marks(result.content)
        assert any(mark.get("type") == "strong" for mark in bold_marks), (
            "Bold text should use 'strong' mark type"
        )

        # Test italic
        result = self.generator.convert_markdown("*italic text*")
        italic_marks = self._extract_marks(result.content)
        assert any(mark.get("type") == "em" for mark in italic_marks), (
            "Italic text should use 'em' mark type"
        )

        # Test link
        result = self.generator.convert_markdown("[link](https://example.com)")
        link_marks = self._extract_marks(result.content)
        assert any(mark.get("type") == "link" for mark in link_marks), (
            "Links should use 'link' mark type"
        )

    def test_specific_node_names(self):
        """Test that specific node names match Outline's schema exactly."""
        # Test code block
        result = self.generator.convert_markdown("```python\nprint('hello')\n```")
        assert any(node.get("type") == "code_block" for node in result.content), (
            "Code blocks should use 'code_block' node type"
        )

        # Test bullet list
        result = self.generator.convert_markdown("- Item 1\n- Item 2")
        assert any(node.get("type") == "bullet_list" for node in result.content), (
            "Bullet lists should use 'bullet_list' node type"
        )

        # Test list items
        list_nodes = [
            node for node in result.content if node.get("type") == "bullet_list"
        ]
        if list_nodes:
            list_content = list_nodes[0].get("content", [])
            assert any(item.get("type") == "list_item" for item in list_content), (
                "List items should use 'list_item' node type"
            )

    def test_no_unsupported_node_types(self):
        """Test that we never generate unsupported node types."""
        # These are common ProseMirror node types that Outline might not support
        unsupported_examples = [
            "codeBlock",  # should be code_block
            "bulletList",  # should be bullet_list
            "listItem",  # should be list_item
            "hardBreak",  # might not be supported
        ]

        # Test comprehensive markdown
        markdown = """
# Heading

Regular paragraph with **bold** and *italic* text.

- List item 1
- List item 2

```python
print("hello world")
```

![Image](image.png)

[Link](https://example.com)
        """.strip()

        result = self.generator.convert_markdown(markdown)
        all_nodes = self._extract_all_nodes(result.content)

        for node in all_nodes:
            node_type = node.get("type")
            assert node_type not in unsupported_examples, (
                f"Generated unsupported node type: {node_type}"
            )
            assert node_type in self.SUPPORTED_NODE_TYPES, (
                f"Generated unknown node type: {node_type}"
            )

    def test_no_unsupported_mark_types(self):
        """Test that we never generate unsupported mark types."""
        # These are mark types we should NOT generate
        unsupported_examples = [
            "bold",  # should be strong
            "italic",  # should be em
            "code",  # should be code_inline (if supported)
        ]

        markdown = "**bold** *italic* [link](https://example.com)"
        result = self.generator.convert_markdown(markdown)
        all_marks = self._extract_marks(result.content)

        for mark in all_marks:
            mark_type = mark.get("type")
            assert mark_type not in unsupported_examples, (
                f"Generated unsupported mark type: {mark_type}"
            )
            assert mark_type in self.SUPPORTED_MARK_TYPES, (
                f"Generated unknown mark type: {mark_type}"
            )

    def test_code_block_attributes(self):
        """Test that code blocks have proper attributes."""
        result = self.generator.convert_markdown("```python\nprint('hello')\n```")
        code_blocks = [
            node for node in result.content if node.get("type") == "code_block"
        ]

        assert len(code_blocks) > 0, "Should generate at least one code block"

        for block in code_blocks:
            attrs = block.get("attrs", {})
            assert "language" in attrs, "Code blocks should have 'language' attribute"
            assert isinstance(attrs["language"], str), "Language should be a string"

    def test_link_attributes(self):
        """Test that links have proper attributes."""
        result = self.generator.convert_markdown("[text](https://example.com)")
        all_marks = self._extract_marks(result.content)
        link_marks = [mark for mark in all_marks if mark.get("type") == "link"]

        assert len(link_marks) > 0, "Should generate at least one link mark"

        for mark in link_marks:
            attrs = mark.get("attrs", {})
            assert "href" in attrs, "Link marks should have 'href' attribute"
            assert isinstance(attrs["href"], str), "href should be a string"

    def test_heading_attributes(self):
        """Test that headings have proper level attributes."""
        for level in range(1, 7):  # H1 through H6
            markdown = f"{'#' * level} Heading {level}"
            result = self.generator.convert_markdown(markdown)
            headings = [
                node for node in result.content if node.get("type") == "heading"
            ]

            assert len(headings) > 0, f"Should generate heading for H{level}"

            for heading in headings:
                attrs = heading.get("attrs", {})
                assert "level" in attrs, "Headings should have 'level' attribute"
                assert attrs["level"] == level, f"H{level} should have level={level}"

    def test_image_attributes(self):
        """Test that images have proper attributes."""
        result = self.generator.convert_markdown("![alt text](image.jpg)")
        all_nodes = self._extract_all_nodes(result.content)
        images = [node for node in all_nodes if node.get("type") == "image"]

        if images:  # Only test if images are generated
            for image in images:
                attrs = image.get("attrs", {})
                assert "src" in attrs, "Images should have 'src' attribute"
                assert isinstance(attrs["src"], str), "src should be a string"
                # alt and title are optional but should be strings if present
                if "alt" in attrs:
                    assert isinstance(attrs["alt"], (str, type(None))), (
                        "alt should be string or None"
                    )
                if "title" in attrs:
                    assert isinstance(attrs["title"], (str, type(None))), (
                        "title should be string or None"
                    )

    def test_outline_database_constraints(self):
        """Test that generated data meets Outline's database validation requirements."""
        from pathlib import Path

        from src.domain.models import TransformedContent
        from src.domain.outline_document_generator import OutlineDocumentGenerator

        # Create test generator
        outline_gen = OutlineDocumentGenerator()

        # Create test content with various lengths to test validation
        test_content = [
            TransformedContent(
                original_path=Path("short.md"),
                markdown="# Short",
                metadata={"title": "A"},  # Short title
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("long_name.md"),
                markdown="# Very Long Title Name",
                metadata={
                    "title": "This is an extremely long document title that definitely exceeds the one hundred character limit and should be truncated by our generator to meet Outline database requirements which have a strict 100 character maximum"
                },
                assets=[],
                warnings=[],
            ),
        ]

        # Generate outline package with a vault name that might be too long
        very_long_vault_name = "This is an extremely long vault name that definitely exceeds the one hundred character limit and should be truncated by our generator to meet Outline database requirements"
        result = outline_gen.generate_outline_package(
            test_content, very_long_vault_name
        )

        # Test Collection constraints
        for collection in result.collections:
            # urlId must be exactly 10 characters
            url_id = collection.get("urlId", "")
            assert len(url_id) == 10, (
                f"Collection urlId '{url_id}' must be exactly 10 characters, got {len(url_id)}"
            )
            assert url_id.isalnum(), (
                f"Collection urlId '{url_id}' should contain only alphanumeric characters for URL safety"
            )

            # name must be 100 characters or less (CollectionValidation.maxNameLength)
            name = collection.get("name", "")
            assert len(name) <= 100, (
                f"Collection name '{name}' must be 100 characters or less, got {len(name)}"
            )

            # icon must be 50 characters or less (if present)
            icon = collection.get("icon")
            if icon is not None:
                assert len(icon) <= 50, (
                    f"Collection icon '{icon}' must be 50 characters or less, got {len(icon)}"
                )

            # color should be hex color (if present)
            color = collection.get("color")
            if color is not None:
                assert isinstance(color, str), "Collection color should be a string"
                if color:  # If not empty
                    assert color.startswith("#"), (
                        f"Collection color '{color}' should be hex color starting with #"
                    )

        # Test Document constraints
        for doc_id, document in result.documents.items():
            # urlId must be exactly 10 characters
            url_id = document.get("urlId", "")
            assert len(url_id) == 10, (
                f"Document urlId '{url_id}' must be exactly 10 characters, got {len(url_id)}"
            )
            assert url_id.isalnum(), (
                f"Document urlId '{url_id}' should contain only alphanumeric characters for URL safety"
            )

            # title must be 100 characters or less (DocumentValidation.maxTitleLength)
            title = document.get("title", "")
            assert len(title) <= 100, (
                f"Document title '{title}' must be 100 characters or less, got {len(title)}"
            )

        # Test that UUIDs are valid format
        assert len(result.collections) > 0, "Should generate at least one collection"
        assert len(result.documents) > 0, "Should generate at least one document"

        # Test collection IDs are valid UUIDs
        for collection in result.collections:
            collection_id = collection.get("id", "")
            assert len(collection_id) == 36, (
                f"Collection ID should be UUID format (36 chars), got {len(collection_id)}"
            )
            assert collection_id.count("-") == 4, (
                "Collection ID should be UUID format with 4 hyphens"
            )

        # Test document IDs are valid UUIDs
        for doc_id in result.documents.keys():
            assert len(doc_id) == 36, (
                f"Document ID should be UUID format (36 chars), got {len(doc_id)}"
            )
            assert doc_id.count("-") == 4, (
                "Document ID should be UUID format with 4 hyphens"
            )

    def test_prosemirror_documents_have_content(self):
        """Test that all ProseMirror documents have at least one content node."""
        test_cases = [
            "",  # Empty markdown
            "   \n\n   ",  # Whitespace only
            "# Title",  # Normal content
            "Paragraph text",  # Simple paragraph
        ]

        for markdown in test_cases:
            result = self.generator.convert_markdown(markdown)

            # Every document must have at least one content node
            assert len(result.content) >= 1, (
                f"Document must have at least one content node, got empty content for markdown: '{markdown}'"
            )

            # Check that content nodes are valid
            for node in result.content:
                assert isinstance(node, dict), "Content nodes must be dictionaries"
                assert "type" in node, "Content nodes must have a type"
                assert node["type"] in self.SUPPORTED_NODE_TYPES, (
                    f"Node type '{node['type']}' is not supported"
                )

    def _validate_node_types(self, content, context=""):
        """Recursively validate all node types in content."""
        for node in content:
            if isinstance(node, dict) and "type" in node:
                node_type = node["type"]
                assert node_type in self.SUPPORTED_NODE_TYPES, (
                    f"Unsupported node type '{node_type}' in {context}"
                )

                # Recursively check content
                if "content" in node:
                    self._validate_node_types(node["content"], context)

    def _validate_mark_types(self, content, context=""):
        """Recursively validate all mark types in content."""
        marks = self._extract_marks(content)
        for mark in marks:
            mark_type = mark.get("type")
            assert mark_type in self.SUPPORTED_MARK_TYPES, (
                f"Unsupported mark type '{mark_type}' in {context}"
            )

    def _extract_marks(self, content):
        """Extract all marks from ProseMirror content."""
        marks = []

        def extract_from_node(node):
            if isinstance(node, dict):
                # Check if this node has marks
                if "marks" in node:
                    marks.extend(node["marks"])

                # Recursively check content
                if "content" in node:
                    for child in node["content"]:
                        extract_from_node(child)

        if isinstance(content, list):
            for node in content:
                extract_from_node(node)
        else:
            extract_from_node(content)

        return marks

    def _extract_all_nodes(self, content):
        """Extract all nodes from ProseMirror content."""
        nodes = []

        def extract_from_content(content_list):
            for node in content_list:
                if isinstance(node, dict):
                    nodes.append(node)
                    if "content" in node:
                        extract_from_content(node["content"])

        if isinstance(content, list):
            extract_from_content(content)

        return nodes
