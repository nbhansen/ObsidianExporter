"""
Test cases for content transformer functionality.

Following TDD approach - these tests define the expected behavior
for the ContentTransformer domain service that orchestrates all
markdown processing and transformation operations.
"""

from pathlib import Path
from unittest.mock import Mock

from src.domain.content_transformer import ContentTransformer
from src.domain.models import ResolvedWikiLink, TransformedContent
from src.infrastructure.parsers.wikilink_parser import WikiLink


class TestContentTransformer:
    """Test suite for ContentTransformer following TDD methodology."""

    def test_transform_content_with_wikilinks(self):
        """
        Test that ContentTransformer processes wikilinks correctly.

        Should parse wikilinks, resolve them, and transform to AppFlowy format.
        """
        # Given: Mock dependencies
        mock_wikilink_parser = Mock()
        mock_wikilink_resolver = Mock()
        mock_callout_parser = Mock()
        mock_block_reference_parser = Mock()
        mock_vault_index = Mock()

        # Mock wikilink parsing
        test_wikilink = WikiLink(
            original="[[test-note]]",
            target="test-note",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )
        mock_wikilink_parser.extract_wikilinks.return_value = [test_wikilink]

        # Mock wikilink resolution
        resolved_wikilink = ResolvedWikiLink(
            original=test_wikilink,
            resolved_path=Path("/vault/test-note.md"),
            is_broken=False,
            target_exists=True,
            resolution_method="filename",
        )
        mock_wikilink_resolver.resolve.return_value = resolved_wikilink

        # Mock callout parser (no callouts in this test)
        mock_callout_parser.transform_callouts.return_value = (
            "This links to [test-note](test-note) which should be resolved."
        )

        # Mock block reference parser (no block references in this test)
        mock_block_reference_parser.transform_block_references.return_value = (
            "This links to [test-note](test-note) which should be resolved."
        )

        transformer = ContentTransformer(
            wikilink_parser=mock_wikilink_parser,
            wikilink_resolver=mock_wikilink_resolver,
            callout_parser=mock_callout_parser,
            block_reference_parser=mock_block_reference_parser,
        )

        original_path = Path("/vault/source.md")
        markdown_content = "This links to [[test-note]] which should be resolved."

        # When: We transform the content
        result = transformer.transform_content(
            original_path=original_path,
            markdown_content=markdown_content,
            vault_index=mock_vault_index,
        )

        # Then: Should return TransformedContent with resolved links
        assert isinstance(result, TransformedContent)
        assert result.original_path == original_path
        assert "test-note" in result.markdown  # Should contain transformed link
        assert len(result.warnings) == 0  # No warnings for successful resolution

        # And: Should have called dependencies correctly
        mock_wikilink_parser.extract_wikilinks.assert_called_once_with(markdown_content)
        mock_wikilink_resolver.resolve.assert_called_once_with(
            test_wikilink, mock_vault_index
        )

    def test_transform_content_with_broken_wikilinks(self):
        """
        Test that ContentTransformer handles broken wikilinks gracefully.

        Should detect broken links and generate appropriate warnings.
        """
        # Given: Mock dependencies with broken wikilink
        mock_wikilink_parser = Mock()
        mock_wikilink_resolver = Mock()
        mock_callout_parser = Mock()
        mock_vault_index = Mock()

        broken_wikilink = WikiLink(
            original="[[nonexistent]]",
            target="nonexistent",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )
        mock_wikilink_parser.extract_wikilinks.return_value = [broken_wikilink]

        # Mock broken resolution
        broken_resolved = ResolvedWikiLink(
            original=broken_wikilink,
            resolved_path=None,
            is_broken=True,
            target_exists=False,
            resolution_method="failed",
        )
        mock_wikilink_resolver.resolve.return_value = broken_resolved

        # Mock callout parser (no callouts in this test)
        mock_callout_parser.transform_callouts.return_value = (
            "This links to [[nonexistent]] which is broken."
        )

        # Mock block reference parser (no block references in this test)
        mock_block_reference_parser = Mock()
        mock_block_reference_parser.transform_block_references.return_value = (
            "This links to [[nonexistent]] which is broken."
        )

        transformer = ContentTransformer(
            wikilink_parser=mock_wikilink_parser,
            wikilink_resolver=mock_wikilink_resolver,
            callout_parser=mock_callout_parser,
            block_reference_parser=mock_block_reference_parser,
        )

        original_path = Path("/vault/source.md")
        markdown_content = "This links to [[nonexistent]] which is broken."

        # When: We transform the content
        result = transformer.transform_content(
            original_path=original_path,
            markdown_content=markdown_content,
            vault_index=mock_vault_index,
        )

        # Then: Should generate warning for broken link
        assert isinstance(result, TransformedContent)
        assert len(result.warnings) == 1
        assert "broken wikilink" in result.warnings[0].lower()
        assert "nonexistent" in result.warnings[0]

    def test_transform_content_preserves_frontmatter(self):
        """
        Test that ContentTransformer extracts and preserves YAML frontmatter.

        Should separate frontmatter from content and include in metadata.
        """
        # Given: Mock dependencies
        mock_wikilink_parser = Mock()
        mock_wikilink_resolver = Mock()
        mock_callout_parser = Mock()
        mock_vault_index = Mock()

        # No wikilinks in this test
        mock_wikilink_parser.extract_wikilinks.return_value = []

        # Mock callout parser (no callouts in this test)
        mock_callout_parser.transform_callouts.return_value = (
            "\n\n# Test Content\n\nThis is the actual content of the note.\n"
        )

        # Mock block reference parser (no block references in this test)
        mock_block_reference_parser = Mock()
        mock_block_reference_parser.transform_block_references.return_value = (
            "\n\n# Test Content\n\nThis is the actual content of the note.\n"
        )

        transformer = ContentTransformer(
            wikilink_parser=mock_wikilink_parser,
            wikilink_resolver=mock_wikilink_resolver,
            callout_parser=mock_callout_parser,
            block_reference_parser=mock_block_reference_parser,
        )

        original_path = Path("/vault/note-with-metadata.md")
        markdown_content = """---
title: Test Note
tags: [project, important]
created: 2023-01-01
---

# Test Content

This is the actual content of the note.
"""

        # When: We transform the content
        result = transformer.transform_content(
            original_path=original_path,
            markdown_content=markdown_content,
            vault_index=mock_vault_index,
        )

        # Then: Should extract frontmatter to metadata
        assert isinstance(result, TransformedContent)
        assert "title" in result.metadata
        assert result.metadata["title"] == "Test Note"
        assert "tags" in result.metadata
        assert result.metadata["tags"] == ["project", "important"]

        # And: Content should not contain frontmatter
        assert "---" not in result.markdown
        assert "title: Test Note" not in result.markdown
        assert "# Test Content" in result.markdown

    def test_transform_content_identifies_assets(self):
        """
        Test that ContentTransformer identifies and tracks asset references.

        Should find image embeds, attachments, and other asset references.
        """
        # Given: Mock dependencies
        mock_wikilink_parser = Mock()
        mock_wikilink_resolver = Mock()
        mock_callout_parser = Mock()
        mock_vault_index = Mock()

        # Mock embed wikilink
        embed_wikilink = WikiLink(
            original="![[diagram.png]]",
            target="diagram.png",
            alias=None,
            header=None,
            block_id=None,
            is_embed=True,
        )
        mock_wikilink_parser.extract_wikilinks.return_value = [embed_wikilink]

        # Mock successful resolution
        resolved_embed = ResolvedWikiLink(
            original=embed_wikilink,
            resolved_path=Path("/vault/assets/diagram.png"),
            is_broken=False,
            target_exists=True,
            resolution_method="filename",
        )
        mock_wikilink_resolver.resolve.return_value = resolved_embed

        # Mock callout parser (no callouts in this test)
        content = (
            "# Visual Content\n\n"
            "Here's an embedded diagram: ![diagram.png](diagram.png)\n\n"
            "And a standard markdown image: ![alt text](./images/photo.jpg)\n"
        )
        mock_callout_parser.transform_callouts.return_value = content

        # Mock block reference parser (no block references in this test)
        mock_block_reference_parser = Mock()
        mock_block_reference_parser.transform_block_references.return_value = content

        transformer = ContentTransformer(
            wikilink_parser=mock_wikilink_parser,
            wikilink_resolver=mock_wikilink_resolver,
            callout_parser=mock_callout_parser,
            block_reference_parser=mock_block_reference_parser,
        )

        original_path = Path("/vault/visual-note.md")
        markdown_content = """# Visual Content

Here's an embedded diagram: ![[diagram.png]]

And a standard markdown image: ![alt text](./images/photo.jpg)
"""

        # When: We transform the content
        result = transformer.transform_content(
            original_path=original_path,
            markdown_content=markdown_content,
            vault_index=mock_vault_index,
        )

        # Then: Should identify asset references
        assert isinstance(result, TransformedContent)
        assert len(result.assets) >= 1  # Should find at least the resolved embed
        assert Path("/vault/assets/diagram.png") in result.assets

    def test_transform_content_handles_empty_content(self):
        """
        Test that ContentTransformer handles empty or minimal content gracefully.
        """
        # Given: Mock dependencies
        mock_wikilink_parser = Mock()
        mock_wikilink_resolver = Mock()
        mock_callout_parser = Mock()
        mock_vault_index = Mock()

        # No wikilinks found
        mock_wikilink_parser.extract_wikilinks.return_value = []

        # Mock callout parser (empty content)
        mock_callout_parser.transform_callouts.return_value = ""

        # Mock block reference parser (empty content)
        mock_block_reference_parser = Mock()
        mock_block_reference_parser.transform_block_references.return_value = ""

        transformer = ContentTransformer(
            wikilink_parser=mock_wikilink_parser,
            wikilink_resolver=mock_wikilink_resolver,
            callout_parser=mock_callout_parser,
            block_reference_parser=mock_block_reference_parser,
        )

        original_path = Path("/vault/empty.md")
        markdown_content = ""

        # When: We transform empty content
        result = transformer.transform_content(
            original_path=original_path,
            markdown_content=markdown_content,
            vault_index=mock_vault_index,
        )

        # Then: Should return valid but empty result
        assert isinstance(result, TransformedContent)
        assert result.original_path == original_path
        assert result.markdown == ""
        assert result.metadata == {}
        assert result.assets == []
        assert result.warnings == []

    def test_transform_content_with_multiple_wikilinks(self):
        """
        Test that ContentTransformer processes multiple wikilinks correctly.

        Should handle various wikilink types in a single document.
        """
        # Given: Mock dependencies with multiple wikilinks
        mock_wikilink_parser = Mock()
        mock_wikilink_resolver = Mock()
        mock_callout_parser = Mock()
        mock_vault_index = Mock()

        # Multiple wikilinks
        wikilinks = [
            WikiLink("[[note1]]", "note1", None, None, None, False),
            WikiLink("[[note2|Alias]]", "note2", "Alias", None, None, False),
            WikiLink("[[note3#Header]]", "note3", None, "Header", None, False),
            WikiLink("![[image.png]]", "image.png", None, None, None, True),
        ]
        mock_wikilink_parser.extract_wikilinks.return_value = wikilinks

        # Mock all as resolved successfully
        def mock_resolve(wikilink, vault_index):
            return ResolvedWikiLink(
                original=wikilink,
                resolved_path=Path(f"/vault/{wikilink.target}.md"),
                is_broken=False,
                target_exists=True,
                resolution_method="filename",
            )

        mock_wikilink_resolver.resolve.side_effect = mock_resolve

        # Mock callout parser (no callouts in this test)
        content = (
            "# Complex Note\n\n"
            "Links to [note1](note1) and [Alias](note2).\n"
            "References [note3](note3#Header) section.\n"
            "Embeds ![image.png](image.png) inline.\n"
        )
        mock_callout_parser.transform_callouts.return_value = content

        # Mock block reference parser (no block references in this test)
        mock_block_reference_parser = Mock()
        mock_block_reference_parser.transform_block_references.return_value = content

        transformer = ContentTransformer(
            wikilink_parser=mock_wikilink_parser,
            wikilink_resolver=mock_wikilink_resolver,
            callout_parser=mock_callout_parser,
            block_reference_parser=mock_block_reference_parser,
        )

        original_path = Path("/vault/complex.md")
        markdown_content = """# Complex Note

Links to [[note1]] and [[note2|Alias]].
References [[note3#Header]] section.
Embeds ![[image.png]] inline.
"""

        # When: We transform the content
        result = transformer.transform_content(
            original_path=original_path,
            markdown_content=markdown_content,
            vault_index=mock_vault_index,
        )

        # Then: Should process all wikilinks
        assert isinstance(result, TransformedContent)
        assert mock_wikilink_resolver.resolve.call_count == 4
        assert len(result.warnings) == 0  # All resolved successfully
