"""
Test cases for wikilink resolver functionality.

Following TDD approach - these tests define the expected behavior
for three-stage wikilink resolution following Obsidian's precedence.
"""

from pathlib import Path
from unittest.mock import Mock

from src.domain.fallback_parser import FallbackParser
from src.domain.models import ResolvedWikiLink, VaultIndex
from src.domain.wikilink_resolver import WikiLinkResolver
from src.infrastructure.parsers.wikilink_parser import WikiLink


class TestWikiLinkResolver:
    """Test suite for WikiLinkResolver following TDD methodology."""

    def test_resolve_exact_path_match_stage_1(self):
        """
        Test Stage 1: Exact path matching takes highest precedence.

        [[folder/note]] should resolve to exact path if it exists.
        """
        # Given: A vault index with nested files
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            files_by_name={
                "note": Path("/vault/note.md"),
                "other": Path("/vault/folder/note.md"),
            },
            all_paths={
                "note.md": Path("/vault/note.md"),
                "folder/note.md": Path("/vault/folder/note.md"),
            },
        )

        wikilink = WikiLink(
            original="[[folder/note]]",
            target="folder/note",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        resolver = WikiLinkResolver()

        # When: We resolve the wikilink
        result = resolver.resolve(wikilink, vault_index)

        # Then: Should resolve to exact path match
        assert isinstance(result, ResolvedWikiLink)
        assert result.original == wikilink
        assert result.resolved_path == Path("/vault/folder/note.md")
        assert result.is_broken is False
        assert result.target_exists is True
        assert result.resolution_method == "exact"

    def test_resolve_filename_match_stage_2(self):
        """
        Test Stage 2: Filename matching when exact path doesn't exist.

        [[note]] should resolve to filename match when no exact path exists.
        """
        # Given: A vault index with filename mapping
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            files_by_name={
                "note": Path("/vault/somewhere/note.md"),
                "other": Path("/vault/other.md"),
            },
            all_paths={
                "somewhere/note.md": Path("/vault/somewhere/note.md"),
                "other.md": Path("/vault/other.md"),
            },
        )

        wikilink = WikiLink(
            original="[[note]]",
            target="note",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        resolver = WikiLinkResolver()

        # When: We resolve the wikilink
        result = resolver.resolve(wikilink, vault_index)

        # Then: Should resolve via filename match
        assert result.resolved_path == Path("/vault/somewhere/note.md")
        assert result.is_broken is False
        assert result.target_exists is True
        assert result.resolution_method == "filename"

    def test_resolve_with_md_extension_fallback(self):
        """
        Test fallback: Try adding .md extension if exact match fails.

        [[note]] should try "note.md" as exact path if "note" fails.
        """
        # Given: A vault index where "note.md" exists as exact path
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            files_by_name={},  # No filename mapping
            all_paths={
                "note.md": Path("/vault/note.md"),
            },
        )

        wikilink = WikiLink(
            original="[[note]]",
            target="note",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        resolver = WikiLinkResolver()

        # When: We resolve the wikilink
        result = resolver.resolve(wikilink, vault_index)

        # Then: Should resolve via .md extension fallback
        assert result.resolved_path == Path("/vault/note.md")
        assert result.is_broken is False
        assert result.target_exists is True
        assert result.resolution_method == "exact"

    def test_resolve_broken_link_detection(self):
        """
        Test that broken links are properly detected and flagged.

        Links that cannot be resolved should be marked as broken.
        """
        # Given: A vault index without the target file
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            files_by_name={
                "other": Path("/vault/other.md"),
            },
            all_paths={
                "other.md": Path("/vault/other.md"),
            },
        )

        wikilink = WikiLink(
            original="[[nonexistent]]",
            target="nonexistent",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        resolver = WikiLinkResolver()

        # When: We resolve the wikilink
        result = resolver.resolve(wikilink, vault_index)

        # Then: Should be marked as broken
        assert result.resolved_path is None
        assert result.is_broken is True
        assert result.target_exists is False
        assert result.resolution_method == "failed"

    def test_resolve_with_header_and_block_references(self):
        """
        Test that header and block references are handled correctly.

        [[note#header]] and [[note^block]] should resolve the base note.
        """
        # Given: A vault with the base note
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            files_by_name={
                "note": Path("/vault/note.md"),
            },
            all_paths={
                "note.md": Path("/vault/note.md"),
            },
        )

        # Test header reference
        header_wikilink = WikiLink(
            original="[[note#Introduction]]",
            target="note",
            alias=None,
            header="Introduction",
            block_id=None,
            is_embed=False,
        )

        # Test block reference
        block_wikilink = WikiLink(
            original="[[note^block123]]",
            target="note",
            alias=None,
            header=None,
            block_id="block123",
            is_embed=False,
        )

        resolver = WikiLinkResolver()

        # When: We resolve both wikilinks
        header_result = resolver.resolve(header_wikilink, vault_index)
        block_result = resolver.resolve(block_wikilink, vault_index)

        # Then: Both should resolve to the base note
        assert header_result.resolved_path == Path("/vault/note.md")
        assert header_result.is_broken is False
        # Resolves via .md extension fallback
        assert header_result.resolution_method == "exact"

        assert block_result.resolved_path == Path("/vault/note.md")
        assert block_result.is_broken is False
        # Resolves via .md extension fallback
        assert block_result.resolution_method == "exact"

    def test_resolve_embed_wikilinks(self):
        """
        Test that embed wikilinks (![[note]]) are resolved same as regular links.

        Embed status should be preserved but resolution works the same.
        """
        # Given: A vault with the target file
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            files_by_name={
                "image": Path("/vault/assets/image.md"),
            },
            all_paths={
                "assets/image.md": Path("/vault/assets/image.md"),
            },
        )

        embed_wikilink = WikiLink(
            original="![[image]]",
            target="image",
            alias=None,
            header=None,
            block_id=None,
            is_embed=True,
        )

        resolver = WikiLinkResolver()

        # When: We resolve the embed wikilink
        result = resolver.resolve(embed_wikilink, vault_index)

        # Then: Should resolve correctly and preserve embed status
        assert result.original.is_embed is True
        assert result.resolved_path == Path("/vault/assets/image.md")
        assert result.is_broken is False
        assert result.resolution_method == "filename"

    def test_resolve_precedence_exact_over_filename(self):
        """
        Test that exact path matching takes precedence over filename matching.

        When both exact path and filename matches exist, exact should win.
        """
        # Given: A vault where both exact path and filename matches exist
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            files_by_name={
                "note": Path("/vault/other/note.md"),  # Filename match
            },
            all_paths={
                "folder/note.md": Path("/vault/folder/note.md"),  # Exact match
                "other/note.md": Path("/vault/other/note.md"),
            },
        )

        wikilink = WikiLink(
            original="[[folder/note]]",
            target="folder/note",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        resolver = WikiLinkResolver()

        # When: We resolve the wikilink
        result = resolver.resolve(wikilink, vault_index)

        # Then: Should choose exact match over filename match
        assert result.resolved_path == Path("/vault/folder/note.md")
        assert result.resolution_method == "exact"

    def test_resolve_stage_3_llm_fallback(self):
        """
        Test Stage 3: LLM-assisted fuzzy matching when exact and filename matching fail.

        Should use fallback parser for intelligent resolution.
        """
        # Given: VaultIndex with files that don't match exactly
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            files_by_name={
                "project-planning": Path("/vault/project-planning.md"),
                "meeting-notes": Path("/vault/meeting-notes.md"),
            },
            all_paths={
                "project-planning.md": Path("/vault/project-planning.md"),
                "meeting-notes.md": Path("/vault/meeting-notes.md"),
            },
        )

        # Mock fallback parser that resolves the fuzzy match
        mock_fallback_parser = Mock(spec=FallbackParser)
        mock_fallback_parser.resolve_wikilink_fallback.return_value = ResolvedWikiLink(
            original=Mock(),
            resolved_path=Path("/vault/project-planning.md"),
            is_broken=False,
            target_exists=True,
            resolution_method="llm_fuzzy_match",
            confidence=0.85,
        )

        # Wikilink that fails exact and filename matching
        wikilink = WikiLink(
            original="[[Project Plan]]",  # Similar to "project-planning" but not exact
            target="Project Plan",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        resolver = WikiLinkResolver(fallback_parser=mock_fallback_parser)

        # When: We resolve the wikilink
        result = resolver.resolve(wikilink, vault_index)

        # Then: Should use LLM fallback and find fuzzy match
        assert result.resolved_path == Path("/vault/project-planning.md")
        assert result.resolution_method == "llm_fuzzy_match"
        assert result.confidence == 0.85
        assert not result.is_broken

        # And: Should have called fallback parser
        mock_fallback_parser.resolve_wikilink_fallback.assert_called_once()

    def test_resolve_stage_3_no_fallback_parser(self):
        """
        Test Stage 3: When no fallback parser is provided.

        Should return failed resolution when no fallback is available.
        """
        # Given: VaultIndex with no matching files
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            files_by_name={
                "unrelated": Path("/vault/unrelated.md"),
            },
            all_paths={
                "unrelated.md": Path("/vault/unrelated.md"),
            },
        )

        wikilink = WikiLink(
            original="[[Nonexistent Note]]",
            target="Nonexistent Note",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        # No fallback parser provided
        resolver = WikiLinkResolver()

        # When: We resolve the wikilink
        result = resolver.resolve(wikilink, vault_index)

        # Then: Should return failed resolution
        assert result.resolved_path is None
        assert result.resolution_method == "failed"
        assert result.confidence == 0.0
        assert result.is_broken is True

    def test_resolve_stage_3_fallback_returns_none(self):
        """
        Test Stage 3: When fallback parser cannot resolve the link.

        Should return failed resolution when LLM fallback also fails.
        """
        # Given: VaultIndex with no matching files
        vault_index = VaultIndex(
            vault_path=Path("/vault"),
            files_by_name={},
            all_paths={},
        )

        # Mock fallback parser that cannot resolve
        mock_fallback_parser = Mock(spec=FallbackParser)
        mock_fallback_parser.resolve_wikilink_fallback.return_value = None

        wikilink = WikiLink(
            original="[[Truly Nonexistent]]",
            target="Truly Nonexistent",
            alias=None,
            header=None,
            block_id=None,
            is_embed=False,
        )

        resolver = WikiLinkResolver(fallback_parser=mock_fallback_parser)

        # When: We resolve the wikilink
        result = resolver.resolve(wikilink, vault_index)

        # Then: Should return failed resolution
        assert result.resolved_path is None
        assert result.resolution_method == "failed"
        assert result.confidence == 0.0
        assert result.is_broken is True

        # And: Should have attempted fallback
        mock_fallback_parser.resolve_wikilink_fallback.assert_called_once()
