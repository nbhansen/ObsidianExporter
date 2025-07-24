"""
Test cases for OutlineDocumentGenerator.

These tests validate the conversion of domain models to Outline JSON format.
"""

from pathlib import Path

from src.domain.models import OutlinePackage, TransformedContent
from src.domain.outline_document_generator import OutlineDocumentGenerator


class TestOutlineDocumentGenerator:
    """Test suite for OutlineDocumentGenerator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = OutlineDocumentGenerator()

    def test_single_document_conversion(self):
        """Test conversion of single document to Outline format."""
        # Given: A single transformed content
        content = TransformedContent(
            original_path=Path("test.md"),
            markdown="# Test Document\n\nThis is a test.",
            metadata={"title": "Test Document"},
            assets=[],
            warnings=[],
        )

        # When: We convert to Outline format
        result = self.generator.generate_outline_package([content], "Test Vault")

        # Then: Result should be proper OutlinePackage
        assert isinstance(result, OutlinePackage)

        # Check metadata
        assert result.metadata["exportVersion"] == 1
        assert "createdAt" in result.metadata

        # Check collections
        assert len(result.collections) == 1
        collection = result.collections[0]
        assert collection["name"] == "Test Vault"
        assert "id" in collection
        assert len(collection["documentStructure"]) == 1

        # Check documents
        assert len(result.documents) == 1
        doc_id = list(result.documents.keys())[0]
        document = result.documents[doc_id]
        assert document["title"] == "Test Document"
        assert document["data"]["type"] == "doc"
        assert len(document["data"]["content"]) == 2  # heading + paragraph

    def test_multiple_documents_conversion(self):
        """Test conversion of multiple documents to Outline format."""
        # Given: Multiple transformed contents
        contents = [
            TransformedContent(
                original_path=Path("doc1.md"),
                markdown="# Document 1\nContent 1",
                metadata={"title": "Document 1"},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("doc2.md"),
                markdown="# Document 2\nContent 2",
                metadata={"title": "Document 2"},
                assets=[],
                warnings=[],
            ),
        ]

        # When: We convert to Outline format
        result = self.generator.generate_outline_package(contents, "Multi Vault")

        # Then: Result should contain all documents
        assert len(result.documents) == 2
        assert len(result.collections[0]["documentStructure"]) == 2

        # Check document titles
        titles = [doc["title"] for doc in result.documents.values()]
        assert "Document 1" in titles
        assert "Document 2" in titles

    def test_nested_folder_structure(self):
        """Test conversion with nested folder structure."""
        # Given: Contents with folder structure
        contents = [
            TransformedContent(
                original_path=Path("folder1/doc1.md"),
                markdown="# Doc 1",
                metadata={},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("folder1/subfolder/doc2.md"),
                markdown="# Doc 2",
                metadata={},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("folder2/doc3.md"),
                markdown="# Doc 3",
                metadata={},
                assets=[],
                warnings=[],
            ),
        ]

        # When: We convert to Outline format
        result = self.generator.generate_outline_package(contents, "Nested Vault")

        # Then: Document structure should reflect folder hierarchy
        collection = result.collections[0]
        doc_structure = collection["documentStructure"]

        # Should have documents organized by folder
        assert len(doc_structure) == 3  # All docs at root level for now
        # (Full nested structure support can be added later)

    def test_documents_with_assets(self):
        """Test conversion of documents with assets."""
        # Given: Content with assets
        asset_path = Path("images/test.png")
        content = TransformedContent(
            original_path=Path("doc_with_image.md"),
            markdown="# Document\n![Test Image](test.png)",
            metadata={},
            assets=[asset_path],
            warnings=[],
        )

        # When: We convert to Outline format
        result = self.generator.generate_outline_package([content], "Asset Vault")

        # Then: Attachments should be created
        assert len(result.attachments) == 1

        attachment_id = list(result.attachments.keys())[0]
        attachment = result.attachments[attachment_id]
        assert attachment["name"] == "test.png"
        assert attachment["key"].startswith("uploads/")
        assert "documentId" in attachment

    def test_documents_with_warnings(self):
        """Test conversion preserves warnings."""
        # Given: Content with warnings
        content = TransformedContent(
            original_path=Path("problem.md"),
            markdown="# Problem Document",
            metadata={},
            assets=[],
            warnings=["Broken link found", "Invalid callout syntax"],
        )

        # When: We convert to Outline format
        result = self.generator.generate_outline_package([content], "Warning Vault")

        # Then: Warnings should be preserved
        assert len(result.warnings) == 2
        assert "Broken link found" in result.warnings
        assert "Invalid callout syntax" in result.warnings

    def test_empty_content_list(self):
        """Test conversion of empty content list."""
        # Given: Empty content list
        contents = []

        # When: We convert to Outline format
        result = self.generator.generate_outline_package(contents, "Empty Vault")

        # Then: Result should have empty collections and documents
        assert len(result.collections) == 1
        assert len(result.collections[0]["documentStructure"]) == 0
        assert len(result.documents) == 0
        assert len(result.attachments) == 0

    def test_document_url_generation(self):
        """Test that document URLs are properly generated."""
        # Given: Content with title
        content = TransformedContent(
            original_path=Path("my-test-document.md"),
            markdown="# My Test Document",
            metadata={"title": "My Test Document"},
            assets=[],
            warnings=[],
        )

        # When: We convert to Outline format
        result = self.generator.generate_outline_package([content], "URL Test")

        # Then: Document structure should have proper URL
        doc_structure = result.collections[0]["documentStructure"][0]
        assert doc_structure["url"].startswith("/doc/")
        assert "my-test-document" in doc_structure["url"].lower() or doc_structure[
            "url"
        ].endswith(doc_structure["id"])

    def test_document_metadata_extraction(self):
        """Test extraction of document metadata fields."""
        # Given: Content with rich metadata
        content = TransformedContent(
            original_path=Path("rich.md"),
            markdown="# Rich Document",
            metadata={
                "title": "Rich Document",
                "tags": ["tag1", "tag2"],
                "created": "2024-01-01",
                "author": "Test Author",
            },
            assets=[],
            warnings=[],
        )

        # When: We convert to Outline format
        result = self.generator.generate_outline_package([content], "Meta Vault")

        # Then: Document should have proper metadata
        document = list(result.documents.values())[0]
        assert document["title"] == "Rich Document"
        assert "createdAt" in document
        assert "updatedAt" in document
        # Additional metadata handling can be expanded

    def test_collection_metadata(self):
        """Test that collection has proper metadata structure."""
        # Given: Simple content
        content = TransformedContent(
            original_path=Path("test.md"),
            markdown="# Test",
            metadata={},
            assets=[],
            warnings=[],
        )

        # When: We convert to Outline format
        result = self.generator.generate_outline_package([content], "Collection Test")

        # Then: Collection should have required fields
        collection = result.collections[0]
        required_fields = ["id", "urlId", "name", "data", "documentStructure"]
        for field in required_fields:
            assert field in collection

        # Collection data should be ProseMirror document
        assert collection["data"]["type"] == "doc"
