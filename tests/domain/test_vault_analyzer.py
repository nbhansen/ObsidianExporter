"""
Test cases for vault analysis functionality.

Following TDD approach - these tests define the expected behavior
before implementation.
"""

from pathlib import Path
from unittest.mock import Mock, call

import pytest

from src.domain.vault_analyzer import VaultAnalyzer


class TestVaultAnalyzer:
    """Test suite for VaultAnalyzer following hexagonal architecture."""

    def test_detect_valid_obsidian_vault_with_obsidian_directory(self):
        """
        Test that a directory with .obsidian/ subdirectory is detected as valid vault.

        This is the primary indicator of an Obsidian vault.
        """
        # Given: A path that contains .obsidian directory
        vault_path = Path("/fake/vault/path")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True

        mock_wikilink_parser = Mock()
        # Return empty list by default
        mock_wikilink_parser.extract_from_file.return_value = []

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When: We check if it's a valid vault
        result = analyzer.is_valid_vault(vault_path)

        # Then: It should be detected as a valid vault
        assert result is True
        mock_file_system.directory_exists.assert_called_once_with(
            vault_path / ".obsidian"
        )

    def test_detect_invalid_vault_without_obsidian_directory(self):
        """
        Test that a directory without .obsidian/ subdirectory is not a valid vault.
        """
        # Given: A path that does not contain .obsidian directory
        vault_path = Path("/fake/regular/directory")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = False

        mock_wikilink_parser = Mock()
        # Return empty list by default
        mock_wikilink_parser.extract_from_file.return_value = []

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When: We check if it's a valid vault
        result = analyzer.is_valid_vault(vault_path)

        # Then: It should not be detected as a valid vault
        assert result is False
        mock_file_system.directory_exists.assert_called_once_with(
            vault_path / ".obsidian"
        )

    def test_detect_invalid_vault_when_path_does_not_exist(self):
        """
        Test that a non-existent path is not detected as a valid vault.
        """
        # Given: A path that does not exist
        vault_path = Path("/nonexistent/path")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = False

        mock_wikilink_parser = Mock()
        # Return empty list by default
        mock_wikilink_parser.extract_from_file.return_value = []

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When: We check if it's a valid vault
        result = analyzer.is_valid_vault(vault_path)

        # Then: It should not be detected as a valid vault
        assert result is False

    def test_scan_vault_finds_markdown_files(self):
        """
        Test that scan_vault correctly discovers all markdown files in a vault.

        This is essential for building the file inventory.
        """
        # Given: A valid vault path with markdown files
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.side_effect = [
            # First call for markdown files
            [
                Path("/test/vault/note1.md"),
                Path("/test/vault/folder/note2.md"),
            ],
            # Second call for all files
            [
                Path("/test/vault/note1.md"),
                Path("/test/vault/folder/note2.md"),
                Path("/test/vault/image.png"),
                Path("/test/vault/document.txt"),
            ],
        ]

        mock_wikilink_parser = Mock()
        # Return empty list by default
        mock_wikilink_parser.extract_from_file.return_value = []

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When: We scan the vault for files
        result = analyzer.scan_vault(vault_path)

        # Then: It should return the markdown files
        assert len(result.markdown_files) == 2
        assert Path("/test/vault/note1.md") in result.markdown_files
        assert Path("/test/vault/folder/note2.md") in result.markdown_files
        assert result.path == vault_path

        # And: It should return the asset files (non-markdown)
        assert len(result.asset_files) == 2
        assert Path("/test/vault/image.png") in result.asset_files
        assert Path("/test/vault/document.txt") in result.asset_files

        # And: The file system should be called with appropriate patterns
        expected_calls = [
            call(vault_path, "**/*.md"),
            call(vault_path, "**/*.*"),
        ]
        mock_file_system.list_files.assert_has_calls(expected_calls)

    def test_scan_vault_finds_asset_files(self):
        """
        Test that scan_vault correctly discovers asset files (images, PDFs, etc.).
        """
        # Given: A valid vault path with various asset files
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.side_effect = [
            # First call for markdown files
            [Path("/test/vault/note.md")],
            # Second call for asset files
            [
                Path("/test/vault/image.png"),
                Path("/test/vault/photo.jpg"),
                Path("/test/vault/document.pdf"),
                Path("/test/vault/video.mp4"),
            ],
        ]

        mock_wikilink_parser = Mock()
        # Return empty list by default
        mock_wikilink_parser.extract_from_file.return_value = []

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When: We scan the vault for files
        result = analyzer.scan_vault(vault_path)

        # Then: It should return the asset files
        assert len(result.asset_files) == 4
        assert Path("/test/vault/image.png") in result.asset_files
        assert Path("/test/vault/photo.jpg") in result.asset_files
        assert Path("/test/vault/document.pdf") in result.asset_files
        assert Path("/test/vault/video.mp4") in result.asset_files

        # And: File system should be called twice with different patterns
        expected_calls = [
            call(vault_path, "**/*.md"),
            call(vault_path, "**/*.*"),
        ]
        mock_file_system.list_files.assert_has_calls(expected_calls)

    def test_scan_vault_raises_error_for_invalid_vault(self):
        """
        Test that scan_vault raises an error when trying to scan an invalid vault.
        """
        # Given: An invalid vault path (no .obsidian directory)
        vault_path = Path("/invalid/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = False

        mock_wikilink_parser = Mock()
        # Return empty list by default
        mock_wikilink_parser.extract_from_file.return_value = []

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When/Then: Scanning should raise a ValueError
        with pytest.raises(ValueError, match="not a valid Obsidian vault"):
            analyzer.scan_vault(vault_path)

    def test_scan_vault_handles_empty_vault(self):
        """
        Test that scan_vault handles vaults with no markdown or asset files.
        """
        # Given: A valid vault path with no files
        vault_path = Path("/empty/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.return_value = []

        mock_wikilink_parser = Mock()
        # Return empty list by default
        mock_wikilink_parser.extract_from_file.return_value = []

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When: We scan the empty vault
        result = analyzer.scan_vault(vault_path)

        # Then: It should return empty lists but valid structure
        assert result.path == vault_path
        assert result.markdown_files == []
        assert result.asset_files == []
        assert result.links == {}
        assert result.metadata == {}

    def test_scan_vault_extracts_wikilinks_from_markdown_files(self):
        """
        Test that scan_vault extracts wikilinks from markdown files.

        Should populate links dictionary. Following TDD Red phase.
        """
        # Given: A valid vault with markdown files containing wikilinks
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.side_effect = [
            # First call for markdown files
            [
                Path("/test/vault/note1.md"),
                Path("/test/vault/note2.md"),
            ],
            # Second call for all files (markdown + assets)
            [
                Path("/test/vault/note1.md"),
                Path("/test/vault/note2.md"),
                Path("/test/vault/image.png"),
            ],
        ]

        # Mock wikilink parser to return specific wikilinks for each file
        mock_wikilink_parser = Mock()
        mock_wikilinks_note1 = [
            Mock(target="Target Note", original="[[Target Note]]"),
            Mock(target="Another Note", original="[[Another Note|Alias]]"),
        ]
        mock_wikilinks_note2 = [
            Mock(target="Third Note", original="[[Third Note]]"),
        ]
        mock_wikilink_parser.extract_from_file.side_effect = [
            mock_wikilinks_note1,  # For note1.md
            mock_wikilinks_note2,  # For note2.md
        ]

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When: We scan the vault
        result = analyzer.scan_vault(vault_path)

        # Then: The links dictionary should be populated with wikilinks from each file
        expected_links = {
            "note1.md": ["Target Note", "Another Note"],
            "note2.md": ["Third Note"],
        }
        assert result.links == expected_links

        # And: The wikilink parser should be called for each markdown file
        expected_parser_calls = [
            call(Path("/test/vault/note1.md")),
            call(Path("/test/vault/note2.md")),
        ]
        mock_wikilink_parser.extract_from_file.assert_has_calls(expected_parser_calls)
