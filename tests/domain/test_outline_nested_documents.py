"""
Test cases for Outline export with nested documents support.

Following TDD approach - these tests define the expected behavior
for exporting folder hierarchies as nested documents in Outline format.
"""

from pathlib import Path

from src.domain.models import (
    FolderStructure,
    OutlinePackage,
    TransformedContent,
)
from src.domain.outline_document_generator import OutlineDocumentGenerator


class TestOutlineDocumentGeneratorNestedDocuments:
    """Test suite for OutlineDocumentGenerator with nested documents."""

    def test_generate_nested_documents_single_folder(self):
        """Test generating nested documents with single folder structure."""
        # Given: Contents in a single folder
        contents = [
            TransformedContent(
                original_path=Path("/vault/folder/note1.md"),
                markdown="# Note 1\n\nContent 1",
                metadata={"title": "Note 1"},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("/vault/folder/note2.md"),
                markdown="# Note 2\n\nContent 2",
                metadata={"title": "Note 2"},
                assets=[],
                warnings=[],
            ),
        ]

        # And: Folder structure with one folder containing two files
        folder_structure = FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[
                FolderStructure(
                    path=Path("/vault/folder"),
                    name="folder",
                    parent_path=Path("/vault"),
                    child_folders=[],
                    markdown_files=[
                        Path("/vault/folder/note1.md"),
                        Path("/vault/folder/note2.md"),
                    ],
                    level=1,
                )
            ],
            markdown_files=[],
            level=0,
        )

        generator = OutlineDocumentGenerator()

        # When: We generate nested documents package
        result = generator.generate_outline_package_with_nested_documents(
            contents, "Test Vault", folder_structure
        )

        # Then: Should create single collection
        assert isinstance(result, OutlinePackage)
        assert len(result.collections) == 1

        collection = result.collections[0]
        assert collection["name"] == "Test Vault"

        # And: Should have 3 documents total (1 root, 1 folder, 2 content)
        assert len(result.documents) == 4  # root + folder + 2 content docs

        # And: Should have folder document with folder icon
        folder_docs = [
            doc for doc in result.documents.values() if doc.get("icon") == "📁"
        ]
        assert len(folder_docs) == 2  # root + 1 folder

        # Find the non-root folder document
        folder_doc = next(
            doc for doc in folder_docs if doc["title"] == "folder"
        )
        assert folder_doc["title"] == "folder"
        assert folder_doc["icon"] == "📁"

        # And: Content documents should have folder as parent
        content_docs = [
            doc for doc in result.documents.values()
            if doc.get("icon") != "📁" and doc["parentDocumentId"] is not None
        ]
        assert len(content_docs) == 2

        for doc in content_docs:
            assert doc["parentDocumentId"] == folder_doc["id"]

    def test_generate_nested_documents_hierarchical_folders(self):
        """Test generating nested documents with hierarchical folder structure."""
        # Given: Contents in nested folders
        contents = [
            TransformedContent(
                original_path=Path("/vault/parent/child/note.md"),
                markdown="# Child Note\n\nNested content",
                metadata={"title": "Child Note"},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("/vault/parent/parent_note.md"),
                markdown="# Parent Note\n\nParent content",
                metadata={"title": "Parent Note"},
                assets=[],
                warnings=[],
            ),
        ]

        # And: Nested folder structure
        folder_structure = FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[
                FolderStructure(
                    path=Path("/vault/parent"),
                    name="parent",
                    parent_path=Path("/vault"),
                    child_folders=[
                        FolderStructure(
                            path=Path("/vault/parent/child"),
                            name="child",
                            parent_path=Path("/vault/parent"),
                            child_folders=[],
                            markdown_files=[Path("/vault/parent/child/note.md")],
                            level=2,
                        )
                    ],
                    markdown_files=[Path("/vault/parent/parent_note.md")],
                    level=1,
                )
            ],
            markdown_files=[],
            level=0,
        )

        generator = OutlineDocumentGenerator()

        # When: We generate nested documents package
        result = generator.generate_outline_package_with_nested_documents(
            contents, "Test Vault", folder_structure
        )

        # Then: Should have correct document hierarchy
        folder_docs = [
            doc for doc in result.documents.values() if doc.get("icon") == "📁"
        ]

        # Find specific folder documents
        root_doc = next(doc for doc in folder_docs if doc["title"] == "vault")
        parent_doc = next(doc for doc in folder_docs if doc["title"] == "parent")
        child_doc = next(doc for doc in folder_docs if doc["title"] == "child")

        # Verify parent-child relationships
        assert parent_doc["parentDocumentId"] == root_doc["id"]
        assert child_doc["parentDocumentId"] == parent_doc["id"]

        # And: Content documents should have correct parents
        parent_note = next(
            doc for doc in result.documents.values()
            if doc.get("title") == "Parent Note"
        )
        child_note = next(
            doc for doc in result.documents.values()
            if doc.get("title") == "Child Note"
        )

        assert parent_note["parentDocumentId"] == parent_doc["id"]
        assert child_note["parentDocumentId"] == child_doc["id"]

    def test_nested_documents_document_structure_hierarchy(self):
        """Test that document structure reflects proper hierarchy."""
        # Given: Simple nested structure
        contents = [
            TransformedContent(
                original_path=Path("/vault/folder/note.md"),
                markdown="# Note\n\nContent",
                metadata={"title": "Note"},
                assets=[],
                warnings=[],
            ),
        ]

        folder_structure = FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[
                FolderStructure(
                    path=Path("/vault/folder"),
                    name="folder",
                    parent_path=Path("/vault"),
                    child_folders=[],
                    markdown_files=[Path("/vault/folder/note.md")],
                    level=1,
                )
            ],
            markdown_files=[],
            level=0,
        )

        generator = OutlineDocumentGenerator()

        # When: We generate nested documents package
        result = generator.generate_outline_package_with_nested_documents(
            contents, "Test Vault", folder_structure
        )

        # Then: Document structure should show hierarchy
        collection = result.collections[0]
        doc_structure = collection["documentStructure"]

        # Should have one top-level item (the folder)
        assert len(doc_structure) == 1

        folder_node = doc_structure[0]
        assert folder_node["title"] == "folder"
        assert len(folder_node["children"]) == 1

        # Folder should contain the note
        note_node = folder_node["children"][0]
        assert note_node["title"] == "Note"
        assert len(note_node["children"]) == 0  # Leaf node

    def test_nested_documents_preserves_wikilink_mapping(self):
        """Test that folder names are included in wikilink mapping."""
        # Given: Content with potential wikilink to folder
        contents = [
            TransformedContent(
                original_path=Path("/vault/note.md"),
                markdown="# Note\n\nSee [[My Folder]] for more info",
                metadata={"title": "Note"},
                assets=[],
                warnings=[],
            ),
        ]

        folder_structure = FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[
                FolderStructure(
                    path=Path("/vault/My Folder"),
                    name="My Folder",
                    parent_path=Path("/vault"),
                    child_folders=[],
                    markdown_files=[],
                    level=1,
                )
            ],
            markdown_files=[Path("/vault/note.md")],
            level=0,
        )

        generator = OutlineDocumentGenerator()

        # When: We generate nested documents package
        result = generator.generate_outline_package_with_nested_documents(
            contents, "Test Vault", folder_structure
        )

        # Then: Should create folder document
        folder_docs = [
            doc for doc in result.documents.values()
            if doc.get("icon") == "📁" and doc["title"] == "My Folder"
        ]
        assert len(folder_docs) == 1

        # And: Should have proper URL ID (10-character hash)
        folder_doc = folder_docs[0]
        assert len(folder_doc["urlId"]) == 10  # Outline requirement

    def test_nested_documents_empty_folders(self):
        """Test handling of empty folders in nested structure."""
        # Given: Empty folder structure
        contents = []

        folder_structure = FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[
                FolderStructure(
                    path=Path("/vault/empty_folder"),
                    name="empty_folder",
                    parent_path=Path("/vault"),
                    child_folders=[],
                    markdown_files=[],
                    level=1,
                )
            ],
            markdown_files=[],
            level=0,
        )

        generator = OutlineDocumentGenerator()

        # When: We generate nested documents package
        result = generator.generate_outline_package_with_nested_documents(
            contents, "Test Vault", folder_structure
        )

        # Then: Should still create folder documents
        folder_docs = [
            doc for doc in result.documents.values() if doc.get("icon") == "📁"
        ]
        assert len(folder_docs) == 2  # root + empty folder

        empty_folder_doc = next(
            doc for doc in folder_docs if doc["title"] == "empty_folder"
        )
        assert empty_folder_doc["icon"] == "📁"

        # And: Document structure should show empty folder
        collection = result.collections[0]
        doc_structure = collection["documentStructure"]

        assert len(doc_structure) == 1
        empty_node = doc_structure[0]
        assert empty_node["title"] == "empty_folder"
        assert len(empty_node["children"]) == 0

    def test_nested_documents_single_collection_created(self):
        """Test that only one collection is created regardless of folder count."""
        # Given: Multiple nested folders
        contents = [
            TransformedContent(
                original_path=Path("/vault/folder1/note1.md"),
                markdown="# Note 1",
                metadata={"title": "Note 1"},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("/vault/folder2/note2.md"),
                markdown="# Note 2",
                metadata={"title": "Note 2"},
                assets=[],
                warnings=[],
            ),
        ]

        folder_structure = FolderStructure(
            path=Path("/vault"),
            name="vault",
            parent_path=None,
            child_folders=[
                FolderStructure(
                    path=Path("/vault/folder1"),
                    name="folder1",
                    parent_path=Path("/vault"),
                    child_folders=[],
                    markdown_files=[Path("/vault/folder1/note1.md")],
                    level=1,
                ),
                FolderStructure(
                    path=Path("/vault/folder2"),
                    name="folder2",
                    parent_path=Path("/vault"),
                    child_folders=[],
                    markdown_files=[Path("/vault/folder2/note2.md")],
                    level=1,
                ),
            ],
            markdown_files=[],
            level=0,
        )

        generator = OutlineDocumentGenerator()

        # When: We generate nested documents package
        result = generator.generate_outline_package_with_nested_documents(
            contents, "Test Vault", folder_structure
        )

        # Then: Should create only one collection
        assert len(result.collections) == 1

        collection = result.collections[0]
        assert collection["name"] == "Test Vault"

        # And: Collection should have 2 top-level items (the folders)
        assert len(collection["documentStructure"]) == 2
