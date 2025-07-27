"""
Test cases for Outline export with folder support.

Following TDD approach - these tests define the expected behavior
for exporting folder hierarchies to Outline format.
"""

from pathlib import Path

from src.domain.models import (
    FolderStructure,
    OutlinePackage,
    TransformedContent,
)
from src.domain.outline_document_generator import OutlineDocumentGenerator


class TestOutlineDocumentGeneratorWithFolders:
    """Test suite for OutlineDocumentGenerator with folder support."""

    def test_generate_outline_package_with_flat_structure(self):
        """Test generating Outline package from flat folder structure."""
        # Given: Transformed contents from flat vault structure
        contents = [
            TransformedContent(
                original_path=Path("/vault/note1.md"),
                markdown="# Note 1\n\nContent 1",
                metadata={"title": "Note 1"},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("/vault/note2.md"),
                markdown="# Note 2\n\nContent 2",
                metadata={"title": "Note 2"},
                assets=[],
                warnings=[],
            ),
        ]

        generator = OutlineDocumentGenerator()

        # When: We generate Outline package
        result = generator.generate_outline_package(contents, "Test Vault")

        # Then: Should create single collection with all documents
        assert isinstance(result, OutlinePackage)
        assert len(result.collections) == 1

        collection = result.collections[0]
        assert collection["name"] == "Test Vault"
        assert len(collection["documentStructure"]) == 2

        # And: Documents should be in flat structure
        doc_structure = collection["documentStructure"]
        assert all(len(doc["children"]) == 0 for doc in doc_structure)

        # And: All documents should be created
        assert len(result.documents) == 2

    def test_generate_outline_package_with_folder_structure(self):
        """Test generating Outline package preserving folder hierarchy."""
        # Given: Transformed contents with folder hierarchy metadata
        contents = [
            TransformedContent(
                original_path=Path("/vault/index.md"),
                markdown="# Index\n\nRoot content",
                metadata={"title": "Index", "folder_path": "/vault"},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("/vault/docs/readme.md"),
                markdown="# Readme\n\nDocumentation content",
                metadata={"title": "Readme", "folder_path": "/vault/docs"},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("/vault/projects/project1.md"),
                markdown="# Project 1\n\nProject content",
                metadata={"title": "Project 1", "folder_path": "/vault/projects"},
                assets=[],
                warnings=[],
            ),
        ]

        generator = OutlineDocumentGenerator()

        # When: We generate Outline package with folder structure
        result = generator.generate_outline_package_with_folders(
            contents, "Test Vault", self._create_test_folder_structure()
        )

        # Then: Should create multiple collections for folders
        assert len(result.collections) == 3  # Root, docs, projects

        # And: Collections should have correct names
        collection_names = {col["name"] for col in result.collections}
        assert "Test Vault" in collection_names
        assert "docs" in collection_names
        assert "projects" in collection_names

        # And: Documents should be distributed correctly
        root_collection = next(
            col for col in result.collections if col["name"] == "Test Vault"
        )
        docs_collection = next(
            col for col in result.collections if col["name"] == "docs"
        )
        projects_collection = next(
            col for col in result.collections if col["name"] == "projects"
        )

        assert len(root_collection["documentStructure"]) == 1  # index.md
        assert len(docs_collection["documentStructure"]) == 1  # readme.md
        assert len(projects_collection["documentStructure"]) == 1  # project1.md

    def test_generate_outline_package_with_nested_folder_structure(self):
        """Test generating Outline package with deeply nested folders."""
        # Given: Deeply nested content structure
        contents = [
            TransformedContent(
                original_path=Path("/vault/projects/active/current.md"),
                markdown="# Current Project\n\nActive work",
                metadata={
                    "title": "Current Project",
                    "folder_path": "/vault/projects/active",
                },
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("/vault/projects/archive/old.md"),
                markdown="# Old Project\n\nArchived work",
                metadata={
                    "title": "Old Project",
                    "folder_path": "/vault/projects/archive",
                },
                assets=[],
                warnings=[],
            ),
        ]

        generator = OutlineDocumentGenerator()

        # When: We generate with nested structure
        result = generator.generate_outline_package_with_folders(
            contents, "Test Vault", self._create_nested_folder_structure()
        )

        # Then: Should create collections for each folder level
        assert len(result.collections) >= 2  # active and archive collections

        # And: Should preserve document relationships
        active_collection = next(
            (col for col in result.collections if col["name"] == "active"), None
        )
        archive_collection = next(
            (col for col in result.collections if col["name"] == "archive"), None
        )

        assert active_collection is not None
        assert archive_collection is not None
        assert len(active_collection["documentStructure"]) == 1
        assert len(archive_collection["documentStructure"]) == 1

    def test_generate_outline_package_with_folder_metadata_fallback(self):
        """Test that generator falls back gracefully when folder metadata is missing."""
        # Given: Contents without folder metadata
        contents = [
            TransformedContent(
                original_path=Path("/vault/note.md"),
                markdown="# Note\n\nContent",
                metadata={"title": "Note"},  # No folder_path
                assets=[],
                warnings=[],
            ),
        ]

        generator = OutlineDocumentGenerator()

        # When: We try to generate with folders but no folder structure provided
        result = generator.generate_outline_package_with_folders(
            contents, "Test Vault", None
        )

        # Then: Should fall back to flat structure
        assert len(result.collections) == 1
        assert result.collections[0]["name"] == "Test Vault"
        assert len(result.collections[0]["documentStructure"]) == 1

    def test_outline_document_structure_preserves_hierarchy(self):
        """Test that document structure within collections preserves folder hierarchy."""
        # Given: Hierarchical content with parent-child relationships
        contents = [
            TransformedContent(
                original_path=Path("/vault/folder/parent.md"),
                markdown="# Parent\n\nParent content",
                metadata={"title": "Parent", "folder_path": "/vault/folder"},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("/vault/folder/subfolder/child.md"),
                markdown="# Child\n\nChild content",
                metadata={"title": "Child", "folder_path": "/vault/folder/subfolder"},
                assets=[],
                warnings=[],
            ),
        ]

        generator = OutlineDocumentGenerator()

        # When: We generate with hierarchical structure
        result = generator.generate_outline_package_with_folders(
            contents, "Test Vault", self._create_parent_child_folder_structure()
        )

        # Then: Should preserve hierarchy in document structure
        # Parent folder collection should contain parent document
        # Child folder collection should contain child document
        # And navigation should reflect the hierarchy

        folder_collection = next(
            col for col in result.collections if col["name"] == "folder"
        )
        subfolder_collection = next(
            col for col in result.collections if col["name"] == "subfolder"
        )

        assert len(folder_collection["documentStructure"]) == 1
        assert len(subfolder_collection["documentStructure"]) == 1

        # Verify document titles match expected hierarchy
        parent_doc = folder_collection["documentStructure"][0]
        child_doc = subfolder_collection["documentStructure"][0]

        assert parent_doc["title"] == "Parent"
        assert child_doc["title"] == "Child"

    def test_outline_package_with_empty_folders(self):
        """Test handling of folders that contain no markdown files."""
        # Given: Folder structure with empty folders
        empty_folder_structure = FolderStructure(
            path=Path("/vault/empty"),
            name="empty",
            parent_path=Path("/vault"),
            child_folders=[],
            markdown_files=[],  # No files
            level=1,
        )

        root_folder = FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[empty_folder_structure],
            markdown_files=[Path("/vault/note.md")],
            level=0,
        )

        contents = [
            TransformedContent(
                original_path=Path("/vault/note.md"),
                markdown="# Note\n\nContent",
                metadata={"title": "Note", "folder_path": "/vault"},
                assets=[],
                warnings=[],
            ),
        ]

        generator = OutlineDocumentGenerator()

        # When: We generate with empty folders
        result = generator.generate_outline_package_with_folders(
            contents, "Test Vault", root_folder
        )

        # Then: Should not create collections for empty folders
        collection_names = {col["name"] for col in result.collections}
        assert "empty" not in collection_names
        assert "Test Vault" in collection_names

        # And: Should only have collections with actual content
        assert all(len(col["documentStructure"]) > 0 for col in result.collections)

    def _create_test_folder_structure(self) -> FolderStructure:
        """Create test folder structure for testing."""
        docs_folder = FolderStructure(
            path=Path("/vault/docs"),
            name="docs",
            parent_path=Path("/vault"),
            child_folders=[],
            markdown_files=[Path("/vault/docs/readme.md")],
            level=1,
        )

        projects_folder = FolderStructure(
            path=Path("/vault/projects"),
            name="projects",
            parent_path=Path("/vault"),
            child_folders=[],
            markdown_files=[Path("/vault/projects/project1.md")],
            level=1,
        )

        return FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[docs_folder, projects_folder],
            markdown_files=[Path("/vault/index.md")],
            level=0,
        )

    def _create_nested_folder_structure(self) -> FolderStructure:
        """Create nested folder structure for testing."""
        active_folder = FolderStructure(
            path=Path("/vault/projects/active"),
            name="active",
            parent_path=Path("/vault/projects"),
            child_folders=[],
            markdown_files=[Path("/vault/projects/active/current.md")],
            level=2,
        )

        archive_folder = FolderStructure(
            path=Path("/vault/projects/archive"),
            name="archive",
            parent_path=Path("/vault/projects"),
            child_folders=[],
            markdown_files=[Path("/vault/projects/archive/old.md")],
            level=2,
        )

        projects_folder = FolderStructure(
            path=Path("/vault/projects"),
            name="projects",
            parent_path=Path("/vault"),
            child_folders=[active_folder, archive_folder],
            markdown_files=[],
            level=1,
        )

        return FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[projects_folder],
            markdown_files=[],
            level=0,
        )

    def _create_parent_child_folder_structure(self) -> FolderStructure:
        """Create parent-child folder structure for testing."""
        subfolder = FolderStructure(
            path=Path("/vault/folder/subfolder"),
            name="subfolder",
            parent_path=Path("/vault/folder"),
            child_folders=[],
            markdown_files=[Path("/vault/folder/subfolder/child.md")],
            level=2,
        )

        folder = FolderStructure(
            path=Path("/vault/folder"),
            name="folder",
            parent_path=Path("/vault"),
            child_folders=[subfolder],
            markdown_files=[Path("/vault/folder/parent.md")],
            level=1,
        )

        return FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[folder],
            markdown_files=[],
            level=0,
        )
