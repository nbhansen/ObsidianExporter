"""
Test cases for vault index builder functionality.

Following TDD approach - these tests define the expected behavior
for building vault indices for wikilink resolution.
"""

from pathlib import Path
from unittest.mock import Mock

from src.domain.models import VaultIndex
from src.domain.vault_index_builder import VaultIndexBuilder


class TestVaultIndexBuilder:
    """Test suite for VaultIndexBuilder following TDD methodology."""

    def test_build_index_creates_file_mappings(self):
        """
        Test that VaultIndexBuilder creates proper file mappings for resolution.

        Following TDD Red phase - this test should fail initially.
        """
        # Given: A mock file system with markdown files
        mock_file_system = Mock()
        mock_file_system.list_files.return_value = [
            Path("/vault/note1.md"),
            Path("/vault/folder/note2.md"),
            Path("/vault/nested/deep/note3.md"),
        ]

        builder = VaultIndexBuilder(file_system=mock_file_system)
        vault_path = Path("/vault")

        # When: We build the index
        result = builder.build_index(vault_path)

        # Then: It should create proper mappings
        assert isinstance(result, VaultIndex)
        assert result.vault_path == vault_path

        # And: files_by_name should map filename stems to full paths
        expected_files_by_name = {
            "note1": Path("/vault/note1.md"),
            "note2": Path("/vault/folder/note2.md"),
            "note3": Path("/vault/nested/deep/note3.md"),
        }
        assert result.files_by_name == expected_files_by_name

        # And: all_paths should map relative paths to full paths
        expected_all_paths = {
            "note1.md": Path("/vault/note1.md"),
            "folder/note2.md": Path("/vault/folder/note2.md"),
            "nested/deep/note3.md": Path("/vault/nested/deep/note3.md"),
        }
        assert result.all_paths == expected_all_paths

    def test_build_index_handles_duplicate_filenames(self):
        """
        Test that VaultIndexBuilder handles duplicate filenames gracefully.

        When multiple files have same name, should prioritize by path hierarchy.
        """
        # Given: Files with duplicate names
        mock_file_system = Mock()
        mock_file_system.list_files.return_value = [
            Path("/vault/note.md"),  # Root level
            Path("/vault/folder/note.md"),  # Subfolder
            Path("/vault/deep/folder/note.md"),  # Deep subfolder
        ]

        builder = VaultIndexBuilder(file_system=mock_file_system)
        vault_path = Path("/vault")

        # When: We build the index
        result = builder.build_index(vault_path)

        # Then: Should prioritize root level file for filename mapping
        assert result.files_by_name["note"] == Path("/vault/note.md")

        # And: All paths should still be mapped correctly
        assert len(result.all_paths) == 3
        assert "note.md" in result.all_paths
        assert "folder/note.md" in result.all_paths
        assert "deep/folder/note.md" in result.all_paths

    def test_build_index_excludes_non_markdown_files(self):
        """
        Test that VaultIndexBuilder only indexes markdown files.
        """
        # Given: Mix of markdown and non-markdown files
        mock_file_system = Mock()
        mock_file_system.list_files.return_value = [
            Path("/vault/note.md"),
            Path("/vault/image.png"),
            Path("/vault/document.txt"),
            Path("/vault/another.md"),
        ]

        builder = VaultIndexBuilder(file_system=mock_file_system)
        vault_path = Path("/vault")

        # When: We build the index
        result = builder.build_index(vault_path)

        # Then: Should only include markdown files
        assert len(result.files_by_name) == 2
        assert "note" in result.files_by_name
        assert "another" in result.files_by_name
        assert "image" not in result.files_by_name
        assert "document" not in result.files_by_name

    def test_build_index_handles_case_sensitivity(self):
        """
        Test that VaultIndexBuilder handles case-sensitive filenames properly.
        """
        # Given: Files with different casing
        mock_file_system = Mock()
        mock_file_system.list_files.return_value = [
            Path("/vault/Note.md"),
            Path("/vault/note.md"),
            Path("/vault/NOTE.md"),
        ]

        builder = VaultIndexBuilder(file_system=mock_file_system)
        vault_path = Path("/vault")

        # When: We build the index
        result = builder.build_index(vault_path)

        # Then: Should handle case-sensitive mapping
        # (Implementation will determine exact behavior)
        assert len(result.files_by_name) >= 1  # At least one mapping
        assert len(result.all_paths) == 3  # All paths preserved

    def test_build_index_with_empty_vault(self):
        """
        Test that VaultIndexBuilder handles empty vaults gracefully.
        """
        # Given: Empty vault
        mock_file_system = Mock()
        mock_file_system.list_files.return_value = []

        builder = VaultIndexBuilder(file_system=mock_file_system)
        vault_path = Path("/vault")

        # When: We build the index
        result = builder.build_index(vault_path)

        # Then: Should return empty but valid index
        assert isinstance(result, VaultIndex)
        assert result.vault_path == vault_path
        assert result.files_by_name == {}
        assert result.all_paths == {}
