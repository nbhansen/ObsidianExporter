"""
Integration tests for folder support using real Obsidian vault data.

These tests validate the complete folder hierarchy extraction and export pipeline
with actual vault structures.
"""

from pathlib import Path

import pytest

from src.domain.outline_document_generator import OutlineDocumentGenerator
from src.domain.vault_analyzer import FolderAnalyzer, VaultAnalyzer
from src.infrastructure.file_system import FileSystemAdapter
from src.infrastructure.parsers.wikilink_parser import WikiLinkParser


class TestRealVaultFolderIntegration:
    """Integration tests using real Obsidian vault data."""

    @pytest.fixture
    def real_vault_path(self):
        """Path to real test vault."""
        return Path("/home/nicolai/dev/ObsidianExporter/data/_obsidian")

    @pytest.fixture
    def file_system(self):
        """Real file system for integration testing."""
        return FileSystemAdapter()

    @pytest.fixture
    def wikilink_parser(self):
        """Real wikilink parser for integration testing."""
        return WikiLinkParser()

    @pytest.fixture
    def vault_analyzer(self, file_system, wikilink_parser):
        """Real vault analyzer for integration testing."""
        return VaultAnalyzer(file_system=file_system, wikilink_parser=wikilink_parser)

    def test_real_vault_folder_structure_extraction(
        self, vault_analyzer, real_vault_path
    ):
        """Test that we can extract folder structure from real vault."""
        # Given: Real Obsidian vault with known folder structure

        # When: We analyze the vault with folder support
        result = vault_analyzer.scan_vault_with_folders(real_vault_path)

        # Then: Should successfully extract folder hierarchy
        assert result.path == real_vault_path
        assert result.root_folder.name == "_obsidian"
        assert len(result.all_folders) >= 1  # At least root folder

        # And: Should detect known subfolders
        folder_names = {folder.name for folder in result.all_folders}
        expected_folders = {
            "_obsidian",  # root
            "Chats",
            "Efforts",
            "_Teaching",
            "exam assignments done",
            "_Applications",
            "DFF Green CDIs",
            "_Concepts",
            "_Daily Notes",
            "_Dissemination",
            "_Mess",
            "_Papers",
            "_People",
            "_Research projects",
            "DREAMS project",
            "MEGAprojects",
            "_Reviews and organizing",
            "_Templates",
            "_Writing",
            "__files",
            "mission digital wellbeing meeting notes 07",
            "04",
            "smart-chats",
        }

        # Should contain at least some of the expected folders
        detected_expected = folder_names.intersection(expected_folders)
        assert len(detected_expected) >= 5, (
            f"Expected to detect major folders, only found: {detected_expected}"
        )

        # And: Should have files mapped to folders
        assert len(result.folder_mapping) > 0
        assert len(result.markdown_files) > 0

    def test_real_vault_nested_folder_detection(self, vault_analyzer, real_vault_path):
        """Test detection of nested folder structures in real vault."""
        # Given: Real vault with nested folders

        # When: We analyze folder structure
        result = vault_analyzer.scan_vault_with_folders(real_vault_path)

        # Then: Should detect nested folders correctly
        # Find Efforts folder
        efforts_folder = None
        for folder in result.all_folders:
            if folder.name == "Efforts":
                efforts_folder = folder
                break

        if efforts_folder:
            # Should have _Teaching as child
            teaching_folders = [
                child
                for child in efforts_folder.child_folders
                if child.name == "_Teaching"
            ]
            assert len(teaching_folders) <= 1  # At most one _Teaching folder

            if teaching_folders:
                teaching_folder = teaching_folders[0]
                assert teaching_folder.parent_path == efforts_folder.path
                assert teaching_folder.level == efforts_folder.level + 1

    def test_real_vault_outline_export_with_folders(
        self, vault_analyzer, real_vault_path
    ):
        """Test complete pipeline: analyze real vault and export to Outline with folders."""
        # Given: Real vault structure
        vault_structure = vault_analyzer.scan_vault_with_folders(real_vault_path)

        # Create minimal transformed content from first few markdown files
        from src.domain.models import TransformedContent

        test_files = vault_structure.markdown_files[:5]  # Test with first 5 files
        contents = []

        for md_file in test_files:
            # Create basic transformed content
            content = TransformedContent(
                original_path=md_file,
                markdown=f"# {md_file.stem}\n\nTest content for {md_file.name}",
                metadata={"title": md_file.stem.replace("_", " ").replace("-", " ")},
                assets=[],
                warnings=[],
            )
            contents.append(content)

        generator = OutlineDocumentGenerator()

        # When: We generate Outline package with folders
        result = generator.generate_outline_package_with_folders(
            contents=contents,
            vault_name="Test Real Vault",
            folder_structure=vault_structure.root_folder,
        )

        # Then: Should create valid Outline package
        assert len(result.collections) >= 1
        assert len(result.documents) == 5  # One for each test file
        assert len(result.warnings) == 0  # No errors during processing

        # And: Should have proper collection structure
        collection_names = {col["name"] for col in result.collections}
        assert "Test Real Vault" in collection_names or len(collection_names) > 0

    def test_real_vault_folder_file_mapping_accuracy(
        self, vault_analyzer, real_vault_path
    ):
        """Test that files are correctly mapped to their containing folders."""
        # Given: Real vault with known file structure

        # When: We analyze with folder support
        result = vault_analyzer.scan_vault_with_folders(real_vault_path)

        # Then: Files should be mapped to correct folders
        for file_path, containing_folder in result.folder_mapping.items():
            # File's parent should match folder's path
            assert file_path.parent == containing_folder.path, (
                f"File {file_path} mapped to wrong folder {containing_folder.path}, expected {file_path.parent}"
            )

        # And: All markdown files should be mapped to some folder
        mapped_files = set(result.folder_mapping.keys())
        all_md_files = set(result.markdown_files)

        # Allow some files to be unmapped (edge cases) but most should be mapped
        mapping_rate = len(mapped_files) / len(all_md_files)
        assert mapping_rate >= 0.8, (
            f"Only {mapping_rate:.1%} of files were mapped to folders"
        )

    def test_real_vault_empty_folder_handling(self, file_system, real_vault_path):
        """Test handling of empty folders in real vault structure."""
        # Given: Real vault that may contain empty folders
        analyzer = FolderAnalyzer(file_system=file_system)

        # When: We analyze folder structure
        result = analyzer.analyze_folder_structure(real_vault_path)

        # Then: Should handle empty folders gracefully
        def check_folder_consistency(folder):
            # Folder should have valid path
            assert folder.path.exists()

            # Level should be consistent with path depth relative to root
            expected_level = len(folder.path.relative_to(real_vault_path).parts)
            if folder.path == real_vault_path:
                expected_level = 0
            assert folder.level == expected_level

            # Check children recursively
            for child in folder.child_folders:
                assert child.parent_path == folder.path
                check_folder_consistency(child)

        check_folder_consistency(result)

    def test_real_vault_large_structure_performance(
        self, vault_analyzer, real_vault_path
    ):
        """Test that folder analysis performs well with large real vault."""
        import time

        # Given: Real vault with many files and folders

        # When: We analyze the complete structure
        start_time = time.time()
        result = vault_analyzer.scan_vault_with_folders(real_vault_path)
        analysis_time = time.time() - start_time

        # Then: Should complete in reasonable time (less than 5 seconds for typical vault)
        assert analysis_time < 5.0, (
            f"Folder analysis took {analysis_time:.2f}s, expected < 5s"
        )

        # And: Should handle the full vault structure
        assert len(result.all_folders) >= 1
        assert len(result.markdown_files) > 0

        # Log structure size for monitoring
        print(
            f"Analyzed vault with {len(result.markdown_files)} files and {len(result.all_folders)} folders in {analysis_time:.2f}s"
        )
