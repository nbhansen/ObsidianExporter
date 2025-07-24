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
