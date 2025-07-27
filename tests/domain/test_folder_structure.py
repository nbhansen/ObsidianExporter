"""
Test cases for folder structure domain models.

Following TDD approach - these tests define the expected behavior
before implementation.
"""

from pathlib import Path

import pytest

from src.domain.models import FolderStructure, VaultStructureWithFolders


class TestFolderStructure:
    """Test suite for FolderStructure following hexagonal architecture."""

    def test_folder_structure_creation_with_all_fields(self):
        """Test that FolderStructure can be created with all required fields."""
        # Given: Valid data for all fields
        path = Path("/test/vault/folder")
        name = "folder"
        parent_path = Path("/test/vault")
        child_folders = []
        markdown_files = [Path("/test/vault/folder/note.md")]
        level = 1

        # When: We create a FolderStructure
        folder = FolderStructure(
            path=path,
            name=name,
            parent_path=parent_path,
            child_folders=child_folders,
            markdown_files=markdown_files,
            level=level,
        )

        # Then: All fields should be set correctly
        assert folder.path == path
        assert folder.name == name
        assert folder.parent_path == parent_path
        assert folder.child_folders == child_folders
        assert folder.markdown_files == markdown_files
        assert folder.level == level

    def test_folder_structure_is_immutable(self):
        """Test that FolderStructure is immutable (frozen dataclass)."""
        # Given: A FolderStructure instance
        folder = FolderStructure(
            path=Path("/test/folder"),
            name="test",
            parent_path=None,
            child_folders=[],
            markdown_files=[],
            level=0,
        )

        # When/Then: Attempting to modify fields should raise AttributeError
        with pytest.raises(AttributeError):
            folder.name = "modified"

        with pytest.raises(AttributeError):
            folder.level = 1

    def test_folder_structure_with_nested_children(self):
        """Test FolderStructure with nested child folders."""
        # Given: A nested folder structure
        child_folder = FolderStructure(
            path=Path("/test/parent/child"),
            name="child",
            parent_path=Path("/test/parent"),
            child_folders=[],
            markdown_files=[Path("/test/parent/child/note.md")],
            level=1,
        )

        parent_folder = FolderStructure(
            path=Path("/test/parent"),
            name="parent",
            parent_path=None,
            child_folders=[child_folder],
            markdown_files=[],
            level=0,
        )

        # Then: Parent should contain child
        assert len(parent_folder.child_folders) == 1
        assert parent_folder.child_folders[0] == child_folder
        assert child_folder.parent_path == parent_folder.path

    def test_folder_structure_root_folder_has_no_parent(self):
        """Test that root folder has no parent path."""
        # Given: A root folder
        root = FolderStructure(
            path=Path("/test/vault"),
            name="vault",
            parent_path=None,
            child_folders=[],
            markdown_files=[],
            level=0,
        )

        # Then: Parent path should be None
        assert root.parent_path is None
        assert root.level == 0

    def test_folder_structure_deep_nesting_levels(self):
        """Test folder structure with multiple levels of nesting."""
        # Given: Deeply nested folder structure
        level_2 = FolderStructure(
            path=Path("/vault/level1/level2"),
            name="level2",
            parent_path=Path("/vault/level1"),
            child_folders=[],
            markdown_files=[],
            level=2,
        )

        level_1 = FolderStructure(
            path=Path("/vault/level1"),
            name="level1",
            parent_path=Path("/vault"),
            child_folders=[level_2],
            markdown_files=[],
            level=1,
        )

        root = FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[level_1],
            markdown_files=[],
            level=0,
        )

        # Then: Levels should be correctly assigned
        assert root.level == 0
        assert level_1.level == 1
        assert level_2.level == 2

        # And: Hierarchy should be preserved
        assert root.child_folders[0] == level_1
        assert level_1.child_folders[0] == level_2


class TestVaultStructureWithFolders:
    """Test suite for VaultStructureWithFolders enhanced model."""

    def test_vault_structure_with_folders_creation(self):
        """Test that VaultStructureWithFolders can be created with folder data."""
        # Given: Vault data with folder structure
        path = Path("/test/vault")
        root_folder = FolderStructure(
            path=path,
            name="vault",
            parent_path=None,
            child_folders=[],
            markdown_files=[],
            level=0,
        )
        all_folders = [root_folder]
        markdown_files = [Path("/test/vault/note.md")]
        asset_files = [Path("/test/vault/image.png")]
        folder_mapping = {Path("/test/vault/note.md"): root_folder}
        links = {"note.md": []}
        metadata = {}

        # When: We create a VaultStructureWithFolders
        vault = VaultStructureWithFolders(
            path=path,
            root_folder=root_folder,
            all_folders=all_folders,
            markdown_files=markdown_files,
            asset_files=asset_files,
            folder_mapping=folder_mapping,
            links=links,
            metadata=metadata,
        )

        # Then: All fields should be set correctly
        assert vault.path == path
        assert vault.root_folder == root_folder
        assert vault.all_folders == all_folders
        assert vault.markdown_files == markdown_files
        assert vault.asset_files == asset_files
        assert vault.folder_mapping == folder_mapping
        assert vault.links == links
        assert vault.metadata == metadata

    def test_vault_structure_with_folders_is_immutable(self):
        """Test that VaultStructureWithFolders is immutable."""
        # Given: A VaultStructureWithFolders instance
        root_folder = FolderStructure(
            path=Path("/test"),
            name="test",
            parent_path=None,
            child_folders=[],
            markdown_files=[],
            level=0,
        )

        vault = VaultStructureWithFolders(
            path=Path("/test"),
            root_folder=root_folder,
            all_folders=[root_folder],
            markdown_files=[],
            asset_files=[],
            folder_mapping={},
            links={},
            metadata={},
        )

        # When/Then: Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            vault.path = Path("/modified")

        with pytest.raises(AttributeError):
            vault.all_folders = []

    def test_vault_structure_with_complex_folder_hierarchy(self):
        """Test VaultStructureWithFolders with complex nested folder structure."""
        # Given: Complex folder hierarchy
        docs_folder = FolderStructure(
            path=Path("/vault/Documents"),
            name="Documents",
            parent_path=Path("/vault"),
            child_folders=[],
            markdown_files=[Path("/vault/Documents/readme.md")],
            level=1,
        )

        projects_folder = FolderStructure(
            path=Path("/vault/Projects"),
            name="Projects",
            parent_path=Path("/vault"),
            child_folders=[],
            markdown_files=[Path("/vault/Projects/project1.md")],
            level=1,
        )

        root_folder = FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[docs_folder, projects_folder],
            markdown_files=[Path("/vault/index.md")],
            level=0,
        )

        all_folders = [root_folder, docs_folder, projects_folder]
        markdown_files = [
            Path("/vault/index.md"),
            Path("/vault/Documents/readme.md"),
            Path("/vault/Projects/project1.md"),
        ]
        folder_mapping = {
            Path("/vault/index.md"): root_folder,
            Path("/vault/Documents/readme.md"): docs_folder,
            Path("/vault/Projects/project1.md"): projects_folder,
        }

        vault = VaultStructureWithFolders(
            path=Path("/vault"),
            root_folder=root_folder,
            all_folders=all_folders,
            markdown_files=markdown_files,
            asset_files=[],
            folder_mapping=folder_mapping,
            links={},
            metadata={},
        )

        # Then: Structure should be correctly represented
        assert len(vault.all_folders) == 3
        assert len(vault.root_folder.child_folders) == 2
        assert vault.folder_mapping[Path("/vault/Documents/readme.md")] == docs_folder
        assert (
            vault.folder_mapping[Path("/vault/Projects/project1.md")] == projects_folder
        )

    def test_vault_structure_folder_mapping_consistency(self):
        """Test that folder mapping correctly maps files to their folders."""
        # Given: Folder structure with files
        folder = FolderStructure(
            path=Path("/vault/folder"),
            name="folder",
            parent_path=Path("/vault"),
            child_folders=[],
            markdown_files=[
                Path("/vault/folder/file1.md"),
                Path("/vault/folder/file2.md"),
            ],
            level=1,
        )

        root = FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[folder],
            markdown_files=[Path("/vault/root.md")],
            level=0,
        )

        folder_mapping = {
            Path("/vault/root.md"): root,
            Path("/vault/folder/file1.md"): folder,
            Path("/vault/folder/file2.md"): folder,
        }

        vault = VaultStructureWithFolders(
            path=Path("/vault"),
            root_folder=root,
            all_folders=[root, folder],
            markdown_files=[
                Path("/vault/root.md"),
                Path("/vault/folder/file1.md"),
                Path("/vault/folder/file2.md"),
            ],
            asset_files=[],
            folder_mapping=folder_mapping,
            links={},
            metadata={},
        )

        # Then: Each file should map to correct folder
        assert vault.folder_mapping[Path("/vault/root.md")] == root
        assert vault.folder_mapping[Path("/vault/folder/file1.md")] == folder
        assert vault.folder_mapping[Path("/vault/folder/file2.md")] == folder
