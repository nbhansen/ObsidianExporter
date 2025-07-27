"""
Test cases for OutlinePackageGenerator.

These tests validate the creation of Outline-compatible ZIP packages.
"""

import json
import tempfile
import zipfile
from pathlib import Path

from src.domain.models import OutlinePackage
from src.infrastructure.generators.outline_package_generator import (
    OutlinePackageGenerator,
)


class TestOutlinePackageGenerator:
    """Test suite for OutlinePackageGenerator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = OutlinePackageGenerator()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_empty_package_generation(self):
        """Test generation of empty package."""
        # Given: Empty OutlinePackage
        package = OutlinePackage(
            metadata={
                "exportVersion": 1,
                "version": "0.78.0-0",
                "createdAt": "2024-07-18T18:18:14.221Z",
                "createdById": "user-uuid",
                "createdByEmail": "user@example.com",
            },
            collections=[
                {
                    "id": "collection-uuid",
                    "urlId": "test-id",
                    "name": "Empty Collection",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [],
                }
            ],
            documents={},
            attachments={},
            warnings=[],
        )

        output_path = self.temp_dir / "empty.zip"

        # When: We generate the package
        result_path = self.generator.generate_package(package, output_path)

        # Then: ZIP file should be created with correct structure
        assert result_path == output_path
        assert output_path.exists()

        with zipfile.ZipFile(output_path, "r") as zf:
            files = zf.namelist()

            # Should contain metadata.json and collection JSON
            assert "metadata.json" in files
            assert "Empty Collection.json" in files

            # Check metadata content
            metadata_content = json.loads(zf.read("metadata.json"))
            assert metadata_content["exportVersion"] == 1
            assert metadata_content["createdById"] == "user-uuid"

            # Check collection content
            collection_content = json.loads(zf.read("Empty Collection.json"))
            assert collection_content["collection"]["name"] == "Empty Collection"
            assert collection_content["documents"] == {}
            assert collection_content["attachments"] == {}

    def test_package_with_documents(self):
        """Test generation of package with documents."""
        # Given: OutlinePackage with documents
        package = OutlinePackage(
            metadata={
                "exportVersion": 1,
                "version": "0.78.0-0",
                "createdAt": "2024-07-18T18:18:14.221Z",
                "createdById": "user-uuid",
                "createdByEmail": "user@example.com",
            },
            collections=[
                {
                    "id": "collection-uuid",
                    "name": "Test Collection",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {
                            "id": "doc-uuid-1",
                            "title": "Document 1",
                            "url": "/doc/document-1-abc123",
                            "children": [],
                        }
                    ],
                }
            ],
            documents={
                "doc-uuid-1": {
                    "id": "doc-uuid-1",
                    "title": "Document 1",
                    "data": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Hello world"}],
                            }
                        ],
                    },
                    "createdAt": "2024-07-18T18:03:41.622Z",
                }
            },
            attachments={},
            warnings=[],
        )

        output_path = self.temp_dir / "with_docs.zip"

        # When: We generate the package
        result_path = self.generator.generate_package(package, output_path)

        # Then: ZIP should contain documents
        assert result_path == output_path
        assert output_path.exists()

        with zipfile.ZipFile(output_path, "r") as zf:
            collection_content = json.loads(zf.read("Test Collection.json"))

            # Check documents are included
            assert "doc-uuid-1" in collection_content["documents"]
            document = collection_content["documents"]["doc-uuid-1"]
            assert document["title"] == "Document 1"
            assert document["data"]["type"] == "doc"

    def test_package_with_attachments(self):
        """Test generation of package with attachments."""
        # Given: Test attachment file
        test_image = self.temp_dir / "test_image.png"
        test_image.write_bytes(b"fake image data")

        package = OutlinePackage(
            metadata={
                "exportVersion": 1,
                "version": "0.78.0-0",
                "createdAt": "2024-07-18T18:18:14.221Z",
                "createdById": "user-uuid",
                "createdByEmail": "user@example.com",
            },
            collections=[
                {
                    "id": "collection-uuid",
                    "name": "Attachment Collection",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [],
                }
            ],
            documents={},
            attachments={
                "attachment-uuid": {
                    "id": "attachment-uuid",
                    "documentId": "doc-uuid",
                    "contentType": "image/png",
                    "name": "test_image.png",
                    "key": "uploads/test_image.png",
                }
            },
            warnings=[],
        )

        output_path = self.temp_dir / "with_attachments.zip"

        # When: We generate the package (provide attachments mapping)
        attachments_mapping = {"attachment-uuid": test_image}
        result_path = self.generator.generate_package(
            package, output_path, attachments_mapping
        )

        # Then: ZIP should contain uploads directory
        assert result_path == output_path
        assert output_path.exists()

        with zipfile.ZipFile(output_path, "r") as zf:
            files = zf.namelist()

            # Should contain attachment in uploads/
            assert "uploads/test_image.png" in files

            # Check attachment data
            attachment_data = zf.read("uploads/test_image.png")
            assert attachment_data == b"fake image data"

    def test_package_with_warnings(self):
        """Test generation of package with warnings - warnings are handled by CLI, not ZIP."""
        # Given: OutlinePackage with warnings
        package = OutlinePackage(
            metadata={
                "exportVersion": 1,
                "version": "0.78.0-0",
                "createdAt": "2024-07-18T18:18:14.221Z",
                "createdById": "user-uuid",
                "createdByEmail": "user@example.com",
            },
            collections=[
                {
                    "id": "collection-uuid",
                    "name": "Warning Collection",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [],
                }
            ],
            documents={},
            attachments={},
            warnings=["Warning 1", "Warning 2", "Broken link found"],
        )

        output_path = self.temp_dir / "with_warnings.zip"

        # When: We generate the package
        result_path = self.generator.generate_package(package, output_path)

        # Then: ZIP should NOT contain warnings.txt (warnings are handled by CLI)
        assert result_path == output_path

        with zipfile.ZipFile(output_path, "r") as zf:
            files = zf.namelist()
            assert "warnings.txt" not in files

            # But should still contain required Outline files
            assert "metadata.json" in files
            assert "Warning Collection.json" in files

    def test_multiple_collections(self):
        """Test generation of package with multiple collections."""
        # Given: OutlinePackage with multiple collections
        package = OutlinePackage(
            metadata={
                "exportVersion": 1,
                "version": "0.78.0-0",
                "createdAt": "2024-07-18T18:18:14.221Z",
                "createdById": "user-uuid",
                "createdByEmail": "user@example.com",
            },
            collections=[
                {
                    "id": "collection-1",
                    "name": "Collection One",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [],
                },
                {
                    "id": "collection-2",
                    "name": "Collection Two",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [],
                },
            ],
            documents={},
            attachments={},
            warnings=[],
        )

        output_path = self.temp_dir / "multiple_collections.zip"

        # When: We generate the package
        result_path = self.generator.generate_package(package, output_path)

        # Then: ZIP should contain multiple collection JSON files
        assert result_path == output_path

        with zipfile.ZipFile(output_path, "r") as zf:
            files = zf.namelist()

            # Should contain both collection files
            assert "Collection One.json" in files
            assert "Collection Two.json" in files
            assert "metadata.json" in files

    def test_multiple_collections_with_isolated_documents(self):
        """Test that each collection contains ONLY its own documents."""
        # Given: Multiple collections with different documents
        package = OutlinePackage(
            metadata={
                "exportVersion": 1,
                "version": "0.78.0-0",
                "createdAt": "2024-07-18T18:18:14.221Z",
                "createdById": "user-uuid",
                "createdByEmail": "user@example.com",
            },
            collections=[
                {
                    "id": "collection-1",
                    "name": "Collection One",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {
                            "id": "doc-1",
                            "title": "Document 1",
                            "url": "/doc/document-1",
                            "children": [],
                        },
                        {
                            "id": "doc-2",
                            "title": "Document 2",
                            "url": "/doc/document-2",
                            "children": [],
                        },
                    ],
                },
                {
                    "id": "collection-2",
                    "name": "Collection Two",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {
                            "id": "doc-3",
                            "title": "Document 3",
                            "url": "/doc/document-3",
                            "children": [],
                        },
                    ],
                },
                {
                    "id": "collection-3",
                    "name": "Empty Collection",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [],
                },
            ],
            documents={
                "doc-1": {
                    "id": "doc-1",
                    "title": "Document 1",
                    "data": {"type": "doc", "content": []},
                    "collectionId": "collection-1",
                },
                "doc-2": {
                    "id": "doc-2",
                    "title": "Document 2",
                    "data": {"type": "doc", "content": []},
                    "collectionId": "collection-1",
                },
                "doc-3": {
                    "id": "doc-3",
                    "title": "Document 3",
                    "data": {"type": "doc", "content": []},
                    "collectionId": "collection-2",
                },
                "doc-4": {
                    "id": "doc-4",
                    "title": "Orphaned Document",
                    "data": {"type": "doc", "content": []},
                    "collectionId": "non-existent",
                },
            },
            attachments={},
            warnings=[],
        )

        output_path = self.temp_dir / "isolated_docs.zip"

        # When: We generate the package
        result_path = self.generator.generate_package(package, output_path)

        # Then: Each collection should contain ONLY its own documents
        with zipfile.ZipFile(output_path, "r") as zf:
            # Check Collection One
            collection_one = json.loads(zf.read("Collection One.json"))
            assert "doc-1" in collection_one["documents"]
            assert "doc-2" in collection_one["documents"]
            assert "doc-3" not in collection_one["documents"]  # MUST NOT contain doc from collection 2
            assert "doc-4" not in collection_one["documents"]  # MUST NOT contain orphaned doc
            assert len(collection_one["documents"]) == 2

            # Check Collection Two
            collection_two = json.loads(zf.read("Collection Two.json"))
            assert "doc-3" in collection_two["documents"]
            assert "doc-1" not in collection_two["documents"]  # MUST NOT contain docs from collection 1
            assert "doc-2" not in collection_two["documents"]  # MUST NOT contain docs from collection 1
            assert "doc-4" not in collection_two["documents"]  # MUST NOT contain orphaned doc
            assert len(collection_two["documents"]) == 1

            # Check Empty Collection
            empty_collection = json.loads(zf.read("Empty Collection.json"))
            assert len(empty_collection["documents"]) == 0  # MUST be empty

    def test_collection_document_filtering(self):
        """Test that documents are filtered based on documentStructure."""
        # Given: Collection with specific documentStructure
        package = OutlinePackage(
            metadata={"exportVersion": 1},
            collections=[
                {
                    "id": "collection-1",
                    "name": "Filtered Collection",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {"id": "doc-a", "title": "Doc A", "url": "/doc/a", "children": []},
                    ],
                }
            ],
            documents={
                "doc-a": {"id": "doc-a", "title": "Doc A", "data": {"type": "doc"}},
                "doc-b": {"id": "doc-b", "title": "Doc B", "data": {"type": "doc"}},
                "doc-c": {"id": "doc-c", "title": "Doc C", "data": {"type": "doc"}},
            },
            attachments={},
            warnings=[],
        )

        output_path = self.temp_dir / "filtered.zip"

        # When: We generate the package
        self.generator.generate_package(package, output_path)

        # Then: Collection should contain only doc-a
        with zipfile.ZipFile(output_path, "r") as zf:
            collection = json.loads(zf.read("Filtered Collection.json"))
            assert "doc-a" in collection["documents"]
            assert "doc-b" not in collection["documents"]
            assert "doc-c" not in collection["documents"]
            assert len(collection["documents"]) == 1

    def test_collection_attachment_filtering(self):
        """Test that attachments are filtered based on their associated documents."""
        # Given: Collections with documents and attachments
        package = OutlinePackage(
            metadata={"exportVersion": 1},
            collections=[
                {
                    "id": "collection-1",
                    "name": "Collection With Attachments",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {"id": "doc-1", "title": "Doc 1", "url": "/doc/1", "children": []},
                    ],
                },
                {
                    "id": "collection-2",
                    "name": "Collection Without Attachments",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {"id": "doc-2", "title": "Doc 2", "url": "/doc/2", "children": []},
                    ],
                },
            ],
            documents={
                "doc-1": {"id": "doc-1", "title": "Doc 1", "data": {"type": "doc"}},
                "doc-2": {"id": "doc-2", "title": "Doc 2", "data": {"type": "doc"}},
            },
            attachments={
                "att-1": {
                    "id": "att-1",
                    "documentId": "doc-1",
                    "name": "image1.png",
                    "contentType": "image/png",
                },
                "att-2": {
                    "id": "att-2",
                    "documentId": "doc-1",
                    "name": "image2.png",
                    "contentType": "image/png",
                },
                "att-3": {
                    "id": "att-3",
                    "documentId": "doc-2",
                    "name": "image3.png",
                    "contentType": "image/png",
                },
                "att-orphan": {
                    "id": "att-orphan",
                    "documentId": "doc-999",
                    "name": "orphan.png",
                    "contentType": "image/png",
                },
            },
            warnings=[],
        )

        output_path = self.temp_dir / "attachment_filtering.zip"

        # When: We generate the package
        self.generator.generate_package(package, output_path)

        # Then: Each collection should contain only attachments for its documents
        with zipfile.ZipFile(output_path, "r") as zf:
            # Check Collection 1 - should have attachments for doc-1
            collection_1 = json.loads(zf.read("Collection With Attachments.json"))
            assert "att-1" in collection_1["attachments"]
            assert "att-2" in collection_1["attachments"]
            assert "att-3" not in collection_1["attachments"]  # Belongs to doc-2
            assert "att-orphan" not in collection_1["attachments"]  # Orphaned
            assert len(collection_1["attachments"]) == 2

            # Check Collection 2 - should have attachments for doc-2
            collection_2 = json.loads(zf.read("Collection Without Attachments.json"))
            assert "att-3" in collection_2["attachments"]
            assert "att-1" not in collection_2["attachments"]  # Belongs to doc-1
            assert "att-2" not in collection_2["attachments"]  # Belongs to doc-1
            assert "att-orphan" not in collection_2["attachments"]  # Orphaned
            assert len(collection_2["attachments"]) == 1

    def test_safe_filename_generation(self):
        """Test that unsafe characters in collection names are handled."""
        # Given: OutlinePackage with unsafe collection name
        package = OutlinePackage(
            metadata={
                "exportVersion": 1,
                "version": "0.78.0-0",
                "createdAt": "2024-07-18T18:18:14.221Z",
                "createdById": "user-uuid",
                "createdByEmail": "user@example.com",
            },
            collections=[
                {
                    "id": "collection-uuid",
                    "name": "Collection/With:Special*Characters?",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [],
                }
            ],
            documents={},
            attachments={},
            warnings=[],
        )

        output_path = self.temp_dir / "safe_names.zip"

        # When: We generate the package
        result_path = self.generator.generate_package(package, output_path)

        # Then: ZIP should contain safely named file
        assert result_path == output_path

        with zipfile.ZipFile(output_path, "r") as zf:
            files = zf.namelist()

            # Should contain sanitized filename
            safe_files = [
                f for f in files if f.endswith(".json") and f != "metadata.json"
            ]
            assert len(safe_files) == 1
            # The exact safe name may vary, but should not contain problematic characters
            safe_name = safe_files[0]
            assert "/" not in safe_name
            assert ":" not in safe_name
            assert "*" not in safe_name
            assert "?" not in safe_name

    def test_output_directory_creation(self):
        """Test that output directory is created if it doesn't exist."""
        # Given: Output path in non-existent directory
        non_existent_dir = self.temp_dir / "new_dir" / "nested"
        output_path = non_existent_dir / "test.zip"

        package = OutlinePackage(
            metadata={"exportVersion": 1},
            collections=[],
            documents={},
            attachments={},
            warnings=[],
        )

        # When: We generate the package
        result_path = self.generator.generate_package(package, output_path)

        # Then: Directory should be created and ZIP should exist
        assert result_path == output_path
        assert output_path.exists()
        assert non_existent_dir.exists()

    def validate_package(self, package_path: Path) -> bool:
        """Test the validate_package method."""
        # Given: Valid package
        package = OutlinePackage(
            metadata={"exportVersion": 1},
            collections=[
                {
                    "id": "test-id",
                    "name": "Test Collection",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [],
                }
            ],
            documents={},
            attachments={},
            warnings=[],
        )

        output_path = self.temp_dir / "validate_test.zip"
        self.generator.generate_package(package, output_path)

        # When: We validate the package
        is_valid = self.generator.validate_package(output_path)

        # Then: Should return True for valid package
        assert is_valid is True

    def test_integration_nested_folders_with_documents(self):
        """Integration test: Verify correct document distribution in nested folder structure."""
        # Given: Complex nested folder structure like real Obsidian vault
        package = OutlinePackage(
            metadata={"exportVersion": 1},
            collections=[
                {
                    "id": "root-collection",
                    "name": "Root",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {"id": "root-doc", "title": "Root Doc", "children": []},
                    ],
                },
                {
                    "id": "folder-a",
                    "name": "Folder A",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {"id": "doc-a1", "title": "Doc A1", "children": []},
                        {"id": "doc-a2", "title": "Doc A2", "children": []},
                    ],
                },
                {
                    "id": "folder-a-subfolder",
                    "name": "Folder A/Subfolder",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {"id": "doc-sub", "title": "Doc Sub", "children": []},
                    ],
                },
                {
                    "id": "folder-b",
                    "name": "Folder B",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {"id": "doc-b1", "title": "Doc B1", "children": []},
                    ],
                },
            ],
            documents={
                "root-doc": {"id": "root-doc", "title": "Root Doc", "data": {"type": "doc"}},
                "doc-a1": {"id": "doc-a1", "title": "Doc A1", "data": {"type": "doc"}},
                "doc-a2": {"id": "doc-a2", "title": "Doc A2", "data": {"type": "doc"}},
                "doc-sub": {"id": "doc-sub", "title": "Doc Sub", "data": {"type": "doc"}},
                "doc-b1": {"id": "doc-b1", "title": "Doc B1", "data": {"type": "doc"}},
            },
            attachments={
                "att-root": {"id": "att-root", "documentId": "root-doc", "name": "root.png"},
                "att-a1": {"id": "att-a1", "documentId": "doc-a1", "name": "a1.png"},
                "att-sub": {"id": "att-sub", "documentId": "doc-sub", "name": "sub.png"},
                "att-b1": {"id": "att-b1", "documentId": "doc-b1", "name": "b1.png"},
            },
            warnings=[],
        )

        output_path = self.temp_dir / "integration_test.zip"

        # When: We generate the package
        self.generator.generate_package(package, output_path)

        # Then: Verify complete isolation of documents and attachments
        with zipfile.ZipFile(output_path, "r") as zf:
            # Root collection
            root = json.loads(zf.read("Root.json"))
            assert list(root["documents"].keys()) == ["root-doc"]
            assert list(root["attachments"].keys()) == ["att-root"]

            # Folder A
            folder_a = json.loads(zf.read("Folder A.json"))
            assert set(folder_a["documents"].keys()) == {"doc-a1", "doc-a2"}
            assert list(folder_a["attachments"].keys()) == ["att-a1"]

            # Subfolder
            subfolder = json.loads(zf.read("Folder A_Subfolder.json"))
            assert list(subfolder["documents"].keys()) == ["doc-sub"]
            assert list(subfolder["attachments"].keys()) == ["att-sub"]

            # Folder B
            folder_b = json.loads(zf.read("Folder B.json"))
            assert list(folder_b["documents"].keys()) == ["doc-b1"]
            assert list(folder_b["attachments"].keys()) == ["att-b1"]

            # Verify NO cross-contamination
            all_collections = [root, folder_a, subfolder, folder_b]
            all_doc_ids = {"root-doc", "doc-a1", "doc-a2", "doc-sub", "doc-b1"}
            
            for collection in all_collections:
                collection_docs = set(collection["documents"].keys())
                # Each collection should have a subset of all docs
                assert collection_docs.issubset(all_doc_ids)
                # No two collections should share documents
                for other in all_collections:
                    if other != collection:
                        other_docs = set(other["documents"].keys())
                        assert collection_docs.isdisjoint(other_docs)

    def test_nested_document_structure_extraction(self):
        """Test that nested document structures are properly extracted."""
        # Given: Collection with nested documentStructure
        package = OutlinePackage(
            metadata={
                "exportVersion": 2,
                "version": "0.4.0",
                "createdAt": "2024-01-01T00:00:00Z",
            },
            collections=[
                {
                    "id": "collection-1",
                    "name": "Test Collection",
                    "data": {"type": "doc", "content": []},
                    "documentStructure": [
                        {
                            "id": "doc-1",
                            "title": "Document 1",
                            "children": [
                                {
                                    "id": "doc-1-1",
                                    "title": "Subdocument 1.1",
                                    "children": [
                                        {
                                            "id": "doc-1-1-1",
                                            "title": "Deep nested doc",
                                            "children": []
                                        }
                                    ]
                                },
                                {
                                    "id": "doc-1-2",
                                    "title": "Subdocument 1.2",
                                    "children": []
                                }
                            ]
                        },
                        {
                            "id": "doc-2",
                            "title": "Document 2",
                            "children": []
                        }
                    ],
                },
            ],
            documents={
                "doc-1": {"id": "doc-1", "title": "Document 1", "data": {"type": "doc"}},
                "doc-1-1": {
                    "id": "doc-1-1",
                    "title": "Subdocument 1.1",
                    "data": {"type": "doc"}
                },
                "doc-1-1-1": {
                    "id": "doc-1-1-1",
                    "title": "Deep nested doc",
                    "data": {"type": "doc"}
                },
                "doc-1-2": {
                    "id": "doc-1-2",
                    "title": "Subdocument 1.2",
                    "data": {"type": "doc"}
                },
                "doc-2": {"id": "doc-2", "title": "Document 2", "data": {"type": "doc"}},
                "doc-unrelated": {
                    "id": "doc-unrelated",
                    "title": "Unrelated Doc",
                    "data": {"type": "doc"}
                },
            },
            attachments={
                "att-1": {"id": "att-1", "documentId": "doc-1", "name": "file1.png"},
                "att-1-1": {
                    "id": "att-1-1",
                    "documentId": "doc-1-1",
                    "name": "file1-1.png"
                },
                "att-deep": {
                    "id": "att-deep",
                    "documentId": "doc-1-1-1",
                    "name": "deep.png"
                },
                "att-unrelated": {
                    "id": "att-unrelated",
                    "documentId": "doc-unrelated",
                    "name": "unrelated.png"
                },
            },
            warnings=[],
        )

        output_path = self.temp_dir / "nested_structure.zip"

        # When: Generate package
        self.generator.generate_package(package, output_path)

        # Then: Verify nested documents are included in collection
        with zipfile.ZipFile(output_path, "r") as zf:
            collection_data = json.loads(zf.read("Test Collection.json"))

            # All nested documents should be included
            collection_docs = collection_data["documents"]
            assert len(collection_docs) == 5  # All documents except doc-unrelated
            assert "doc-1" in collection_docs
            assert "doc-1-1" in collection_docs
            assert "doc-1-1-1" in collection_docs
            assert "doc-1-2" in collection_docs
            assert "doc-2" in collection_docs
            assert "doc-unrelated" not in collection_docs

            # All attachments for nested documents should be included
            collection_attachments = collection_data["attachments"]
            assert len(collection_attachments) == 3  # All except att-unrelated
            assert "att-1" in collection_attachments
            assert "att-1-1" in collection_attachments
            assert "att-deep" in collection_attachments
            assert "att-unrelated" not in collection_attachments
