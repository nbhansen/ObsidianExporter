"""
Integration test for folder support using the _obsidian_clauded vault.

This test validates the complete folder hierarchy extraction and export pipeline
with a well-organized real vault structure.
"""

import pytest
from pathlib import Path

from src.domain.vault_analyzer import VaultAnalyzer
from src.domain.outline_document_generator import OutlineDocumentGenerator
from src.infrastructure.file_system import FileSystemAdapter
from src.infrastructure.parsers.wikilink_parser import WikiLinkParser


class TestClaudedVaultFolderIntegration:
    """Integration tests using the _obsidian_clauded vault."""

    @pytest.fixture
    def clauded_vault_path(self):
        """Path to the _obsidian_clauded test vault."""
        return Path("/home/nicolai/Documents/_obsidian_clauded")

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

    def test_clauded_vault_folder_structure_extraction(self, vault_analyzer, clauded_vault_path):
        """Test folder structure extraction from the organized _obsidian_clauded vault."""
        # Given: Well-organized Obsidian vault with clear hierarchy
        
        # When: We analyze the vault with folder support
        result = vault_analyzer.scan_vault_with_folders(clauded_vault_path)
        
        # Then: Should successfully extract folder hierarchy
        assert result.path == clauded_vault_path
        assert result.root_folder.name == "_obsidian_clauded"
        assert len(result.all_folders) >= 6  # At least the 6 main top-level folders
        
        # And: Should detect the main organizational folders
        folder_names = {folder.name for folder in result.all_folders}
        expected_main_folders = {
            "_obsidian_clauded",  # root
            "01-ACTIVE-PROJECTS",
            "02-RESEARCH-ARCHIVE", 
            "03-ACADEMIC-ADMIN",
            "04-KNOWLEDGE-BASE",
            "05-WRITING-WORKSPACE",
            "06-SYSTEMS"
        }
        
        # Should contain all main organizational folders
        detected_main = folder_names.intersection(expected_main_folders)
        assert len(detected_main) == len(expected_main_folders), (
            f"Expected all main folders, missing: {expected_main_folders - detected_main}"
        )
        
        # And: Should detect nested subfolders
        expected_nested_folders = {
            "ADHD-Research",
            "AI-Design-Research", 
            "Citizen-Empowerment",
            "DREAMS-Project",
            "Teaching-Current",
            "Completed-Projects",
            "Conference-Reviews",
            "Career-Development",
            "Funding-Applications",
            "Teaching-Archive",
            "Design-Methods",
            "Literature-Papers",
            "People-Network",
            "Research-Concepts",
            "Active-Papers",
            "Drafts-Ideas",
            "Daily-Notes",
            "Inbox-Processing",
            "MOCs-Navigation",
            "Templates"
        }
        
        detected_nested = folder_names.intersection(expected_nested_folders)
        assert len(detected_nested) >= 15, (
            f"Expected many nested folders, only found: {len(detected_nested)}"
        )
        
        # And: Should have files mapped to folders
        assert len(result.folder_mapping) > 0
        assert len(result.markdown_files) > 0

    def test_clauded_vault_hierarchical_organization(self, vault_analyzer, clauded_vault_path):
        """Test that hierarchical organization is correctly preserved."""
        # Given: Vault with 3-level hierarchy
        
        # When: We analyze folder structure
        result = vault_analyzer.scan_vault_with_folders(clauded_vault_path)
        
        # Then: Should preserve 3-level hierarchy correctly
        # Level 0: Root (_obsidian_clauded)
        root_folder = result.root_folder
        assert root_folder.level == 0
        assert len(root_folder.child_folders) >= 6  # Main sections
        
        # Level 1: Main sections (e.g., 01-ACTIVE-PROJECTS)
        active_projects = None
        for child in root_folder.child_folders:
            if child.name == "01-ACTIVE-PROJECTS":
                active_projects = child
                break
        
        assert active_projects is not None
        assert active_projects.level == 1
        assert active_projects.parent_path == clauded_vault_path
        assert len(active_projects.child_folders) >= 4  # ADHD-Research, AI-Design-Research, etc.
        
        # Level 2: Project-specific folders (e.g., ADHD-Research)
        adhd_folder = None
        for child in active_projects.child_folders:
            if child.name == "ADHD-Research":
                adhd_folder = child
                break
        
        if adhd_folder:
            assert adhd_folder.level == 2
            assert adhd_folder.parent_path == active_projects.path
            # Should have markdown files
            assert len(adhd_folder.markdown_files) > 0

    def test_clauded_vault_outline_export_preserves_organization(self, vault_analyzer, clauded_vault_path):
        """Test that Outline export preserves the organizational structure."""
        # Given: Well-organized vault structure
        vault_structure = vault_analyzer.scan_vault_with_folders(clauded_vault_path)
        
        # Create sample transformed content from a few files in different folders
        from src.domain.models import TransformedContent
        
        # Select files from different organizational sections
        test_files = []
        for md_file in vault_structure.markdown_files:
            if any(section in str(md_file) for section in [
                "01-ACTIVE-PROJECTS", "04-KNOWLEDGE-BASE", "06-SYSTEMS"
            ]):
                test_files.append(md_file)
                if len(test_files) >= 6:  # Test with 6 files from different sections
                    break
        
        contents = []
        for md_file in test_files:
            content = TransformedContent(
                original_path=md_file,
                markdown=f"# {md_file.stem}\n\nTest content for {md_file.name}",
                metadata={"title": md_file.stem.replace("_", " ").replace("-", " ")},
                assets=[],
                warnings=[]
            )
            contents.append(content)
        
        generator = OutlineDocumentGenerator()
        
        # When: We generate Outline package with folders
        result = generator.generate_outline_package_with_folders(
            contents=contents,
            vault_name="Clauded Research Vault",
            folder_structure=vault_structure.root_folder
        )
        
        # Then: Should create multiple collections preserving organization
        assert len(result.collections) >= 3  # At least 3 different sections
        assert len(result.documents) == len(test_files)
        assert len(result.warnings) == 0
        
        # And: Should have collections named after organizational folders
        collection_names = {col["name"] for col in result.collections}
        
        # Should contain section-specific collections
        expected_sections = ["01-ACTIVE-PROJECTS", "04-KNOWLEDGE-BASE", "06-SYSTEMS"]
        found_sections = [section for section in expected_sections 
                         if any(section in name for name in collection_names)]
        assert len(found_sections) > 0, f"Expected section collections, got: {collection_names}"

    def test_clauded_vault_performance_with_large_structure(self, vault_analyzer, clauded_vault_path):
        """Test performance with the large, well-organized vault structure."""
        import time
        
        # Given: Large vault with many nested folders and files
        
        # When: We analyze the complete structure
        start_time = time.time()
        result = vault_analyzer.scan_vault_with_folders(clauded_vault_path)
        analysis_time = time.time() - start_time
        
        # Then: Should complete in reasonable time
        assert analysis_time < 3.0, f"Analysis took {analysis_time:.2f}s, expected < 3s"
        
        # And: Should handle the complex structure
        assert len(result.all_folders) >= 20  # Many folders
        assert len(result.markdown_files) >= 50  # Many files
        
        # Log structure analysis
        print(f"\nClauded vault analysis:")
        print(f"  - {len(result.markdown_files)} markdown files")
        print(f"  - {len(result.all_folders)} folders")
        print(f"  - {len(result.folder_mapping)} file mappings")
        print(f"  - Analysis time: {analysis_time:.2f}s")
        
        # Verify folder hierarchy levels
        level_counts = {}
        for folder in result.all_folders:
            level = folder.level
            level_counts[level] = level_counts.get(level, 0) + 1
        
        print(f"  - Folder levels: {dict(sorted(level_counts.items()))}")
        
        # Should have 3 levels: root (0), main sections (1), subsections (2)
        assert 0 in level_counts  # Root level
        assert 1 in level_counts  # Main sections
        assert 2 in level_counts  # Subsections

    def test_clauded_vault_file_distribution_accuracy(self, vault_analyzer, clauded_vault_path):
        """Test that files are correctly distributed across the folder structure."""
        # Given: Vault with known organizational structure
        
        # When: We analyze with folder support
        result = vault_analyzer.scan_vault_with_folders(clauded_vault_path)
        
        # Then: Files should be properly distributed
        # Check that main sections have files
        main_section_files = {}
        for file_path, containing_folder in result.folder_mapping.items():
            # Find the main section (level 1 folder)
            current_folder = containing_folder
            while current_folder.level > 1 and current_folder.parent_path:
                # Find parent folder
                parent = None
                for folder in result.all_folders:
                    if folder.path == current_folder.parent_path:
                        parent = folder
                        break
                if parent:
                    current_folder = parent
                else:
                    break
            
            if current_folder.level == 1:
                section_name = current_folder.name
                if section_name not in main_section_files:
                    main_section_files[section_name] = 0
                main_section_files[section_name] += 1
        
        # Should have files in multiple main sections
        assert len(main_section_files) >= 4, f"Files should be in multiple sections: {main_section_files}"
        
        # Main sections should have reasonable file counts
        for section, count in main_section_files.items():
            assert count > 0, f"Section {section} should have files"
        
        print(f"\nFile distribution across main sections:")
        for section, count in sorted(main_section_files.items()):
            print(f"  - {section}: {count} files")