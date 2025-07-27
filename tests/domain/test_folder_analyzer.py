"""
Test cases for folder analysis functionality.

Following TDD approach - these tests define the expected behavior
for extracting folder structure from Obsidian vaults.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.domain.models import VaultStructureWithFolders
from src.domain.vault_analyzer import FolderAnalyzer


class TestFolderAnalyzer:
    """Test suite for FolderAnalyzer following hexagonal architecture."""

    def test_analyze_simple_flat_vault_structure(self):
        """Test analyzing vault with no subfolders (all files in root)."""
        # Given: A vault with files only in root directory
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.return_value = [
            Path("/test/vault/note1.md"),
            Path("/test/vault/note2.md"),
            Path("/test/vault/image.png"),
        ]

        analyzer = FolderAnalyzer(file_system=mock_file_system)

        # When: We analyze the folder structure
        result = analyzer.analyze_folder_structure(vault_path)

        # Then: Should return single root folder containing all files
        assert result.path == vault_path
        assert result.name == "vault"
        assert result.parent_path is None
        assert result.level == 0
        assert len(result.child_folders) == 0

        # And: Root folder should contain markdown files
        expected_md_files = [
            Path("/test/vault/note1.md"),
            Path("/test/vault/note2.md"),
        ]
        assert result.markdown_files == expected_md_files

    def test_analyze_vault_with_single_subfolder(self):
        """Test analyzing vault with one level of subfolders."""
        # Given: A vault with one subfolder containing files
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.return_value = [
            Path("/test/vault/root.md"),
            Path("/test/vault/docs/readme.md"),
            Path("/test/vault/docs/guide.md"),
            Path("/test/vault/image.png"),
        ]

        analyzer = FolderAnalyzer(file_system=mock_file_system)

        # When: We analyze the folder structure
        result = analyzer.analyze_folder_structure(vault_path)

        # Then: Should return root folder with one child folder
        assert result.path == vault_path
        assert result.name == "vault"
        assert result.level == 0
        assert len(result.child_folders) == 1

        # And: Child folder should be correctly structured
        docs_folder = result.child_folders[0]
        assert docs_folder.path == Path("/test/vault/docs")
        assert docs_folder.name == "docs"
        assert docs_folder.parent_path == vault_path
        assert docs_folder.level == 1
        assert len(docs_folder.child_folders) == 0

        # And: Files should be in correct folders
        assert result.markdown_files == [Path("/test/vault/root.md")]
        expected_docs_files = [
            Path("/test/vault/docs/readme.md"),
            Path("/test/vault/docs/guide.md"),
        ]
        assert docs_folder.markdown_files == expected_docs_files

    def test_analyze_vault_with_nested_subfolders(self):
        """Test analyzing vault with multiple levels of nested folders."""
        # Given: A vault with deeply nested folder structure
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.return_value = [
            Path("/test/vault/index.md"),
            Path("/test/vault/projects/project1.md"),
            Path("/test/vault/projects/active/current.md"),
            Path("/test/vault/projects/active/draft.md"),
            Path("/test/vault/projects/archive/old.md"),
            Path("/test/vault/docs/readme.md"),
        ]

        analyzer = FolderAnalyzer(file_system=mock_file_system)

        # When: We analyze the folder structure
        result = analyzer.analyze_folder_structure(vault_path)

        # Then: Should return correctly nested structure
        assert result.level == 0
        assert len(result.child_folders) == 2  # projects and docs

        # Find projects folder
        projects_folder = next(f for f in result.child_folders if f.name == "projects")
        assert projects_folder.level == 1
        assert len(projects_folder.child_folders) == 2  # active and archive

        # Find active folder
        active_folder = next(
            f for f in projects_folder.child_folders if f.name == "active"
        )
        assert active_folder.level == 2
        assert active_folder.parent_path == projects_folder.path
        assert len(active_folder.child_folders) == 0

        # Verify file distribution
        assert result.markdown_files == [Path("/test/vault/index.md")]
        assert projects_folder.markdown_files == [
            Path("/test/vault/projects/project1.md")
        ]
        expected_active_files = [
            Path("/test/vault/projects/active/current.md"),
            Path("/test/vault/projects/active/draft.md"),
        ]
        assert active_folder.markdown_files == expected_active_files

    def test_analyze_empty_vault_structure(self):
        """Test analyzing vault with no files."""
        # Given: Empty vault
        vault_path = Path("/test/empty")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.return_value = []

        analyzer = FolderAnalyzer(file_system=mock_file_system)

        # When: We analyze the folder structure
        result = analyzer.analyze_folder_structure(vault_path)

        # Then: Should return empty root folder
        assert result.path == vault_path
        assert result.name == "empty"
        assert result.level == 0
        assert len(result.child_folders) == 0
        assert result.markdown_files == []

    def test_analyze_folder_structure_ignores_obsidian_directory(self):
        """Test that .obsidian directory is ignored in folder analysis."""
        # Given: Vault with .obsidian directory containing files
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.return_value = [
            Path("/test/vault/note.md"),
            Path("/test/vault/.obsidian/config.json"),
            Path("/test/vault/.obsidian/themes/theme.css"),
        ]

        analyzer = FolderAnalyzer(file_system=mock_file_system)

        # When: We analyze the folder structure
        result = analyzer.analyze_folder_structure(vault_path)

        # Then: .obsidian folder should be ignored
        assert len(result.child_folders) == 0
        assert result.markdown_files == [Path("/test/vault/note.md")]

        # And: No .obsidian files should be included
        for folder in result.child_folders:
            assert ".obsidian" not in str(folder.path)

    def test_analyze_folder_structure_handles_complex_paths(self):
        """Test folder analysis with complex path names and special characters."""
        # Given: Vault with folders containing spaces and special characters
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.return_value = [
            Path("/test/vault/My Documents/important.md"),
            Path("/test/vault/Project-2024/specs.md"),
            Path("/test/vault/Archive (Old)/legacy.md"),
        ]

        analyzer = FolderAnalyzer(file_system=mock_file_system)

        # When: We analyze the folder structure
        result = analyzer.analyze_folder_structure(vault_path)

        # Then: Should handle special characters correctly
        assert len(result.child_folders) == 3

        folder_names = {f.name for f in result.child_folders}
        assert "My Documents" in folder_names
        assert "Project-2024" in folder_names
        assert "Archive (Old)" in folder_names


class TestVaultAnalyzerWithFolders:
    """Test suite for enhanced VaultAnalyzer with folder support."""

    def test_scan_vault_with_folders_returns_enhanced_structure(self):
        """Test that scan_vault_with_folders returns VaultStructureWithFolders."""
        # Given: A valid vault with folder structure
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.side_effect = [
            # First call: scan_vault() calls for markdown files
            [
                Path("/test/vault/index.md"),
                Path("/test/vault/docs/readme.md"),
            ],
            # Second call: scan_vault() calls for all files
            [
                Path("/test/vault/index.md"),
                Path("/test/vault/docs/readme.md"),
                Path("/test/vault/image.png"),
            ],
            # Third call: FolderAnalyzer calls for all files
            [
                Path("/test/vault/index.md"),
                Path("/test/vault/docs/readme.md"),
                Path("/test/vault/image.png"),
            ],
        ]

        mock_wikilink_parser = Mock()
        mock_wikilink_parser.extract_from_file.return_value = []

        from src.domain.vault_analyzer import VaultAnalyzer

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When: We scan with folder support
        result = analyzer.scan_vault_with_folders(vault_path)

        # Then: Should return VaultStructureWithFolders
        assert isinstance(result, VaultStructureWithFolders)
        assert result.path == vault_path

        # And: Should contain folder structure
        assert result.root_folder.name == "vault"
        assert len(result.all_folders) >= 1  # At least root folder

        # And: Should have folder mapping
        assert len(result.folder_mapping) >= 2  # At least two files mapped

        # And: Should preserve original structure data
        assert len(result.markdown_files) == 2
        assert len(result.asset_files) == 1

    def test_scan_vault_with_folders_builds_correct_folder_mapping(self):
        """Test that folder mapping correctly maps files to folders."""
        # Given: Vault with files in different folders
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.side_effect = [
            # First call: scan_vault() markdown files
            [
                Path("/test/vault/root.md"),
                Path("/test/vault/folder/nested.md"),
            ],
            # Second call: scan_vault() all files
            [
                Path("/test/vault/root.md"),
                Path("/test/vault/folder/nested.md"),
            ],
            # Third call: FolderAnalyzer all files
            [
                Path("/test/vault/root.md"),
                Path("/test/vault/folder/nested.md"),
            ],
        ]

        mock_wikilink_parser = Mock()
        mock_wikilink_parser.extract_from_file.return_value = []

        from src.domain.vault_analyzer import VaultAnalyzer

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When: We scan with folder support
        result = analyzer.scan_vault_with_folders(vault_path)

        # Then: Files should be mapped to correct folders
        root_file = Path("/test/vault/root.md")
        nested_file = Path("/test/vault/folder/nested.md")

        assert root_file in result.folder_mapping
        assert nested_file in result.folder_mapping

        # And: Root file should map to root folder
        assert result.folder_mapping[root_file] == result.root_folder

        # And: Nested file should map to subfolder
        nested_folder = result.folder_mapping[nested_file]
        assert nested_folder.name == "folder"
        assert nested_folder.parent_path == vault_path

    def test_scan_vault_with_folders_preserves_original_behavior(self):
        """Test that enhanced scanning preserves all original VaultStructure data."""
        # Given: Vault setup similar to original tests
        vault_path = Path("/test/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = True
        mock_file_system.list_files.side_effect = [
            # First call: scan_vault() markdown files
            [Path("/test/vault/note.md")],
            # Second call: scan_vault() all files
            [Path("/test/vault/note.md"), Path("/test/vault/image.png")],
            # Third call: FolderAnalyzer all files
            [Path("/test/vault/note.md"), Path("/test/vault/image.png")],
        ]

        mock_wikilink_parser = Mock()
        mock_wikilinks = [Mock(target="Target", original="[[Target]]")]
        mock_wikilink_parser.extract_from_file.return_value = mock_wikilinks

        from src.domain.vault_analyzer import VaultAnalyzer

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When: We scan with folder support
        result = analyzer.scan_vault_with_folders(vault_path)

        # Then: Original data should be preserved
        assert result.path == vault_path
        assert result.markdown_files == [Path("/test/vault/note.md")]
        assert result.asset_files == [Path("/test/vault/image.png")]
        assert result.links == {"note.md": ["Target"]}
        assert result.metadata == {}

    def test_scan_vault_with_folders_raises_error_for_invalid_vault(self):
        """Test that scanning invalid vault raises appropriate error."""
        # Given: Invalid vault path
        vault_path = Path("/invalid/vault")
        mock_file_system = Mock()
        mock_file_system.directory_exists.return_value = False

        mock_wikilink_parser = Mock()

        from src.domain.vault_analyzer import VaultAnalyzer

        analyzer = VaultAnalyzer(
            file_system=mock_file_system, wikilink_parser=mock_wikilink_parser
        )

        # When/Then: Should raise ValueError
        with pytest.raises(ValueError, match="not a valid Obsidian vault"):
            analyzer.scan_vault_with_folders(vault_path)
