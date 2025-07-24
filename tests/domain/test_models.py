"""
Test cases for domain models.

These tests validate the immutable data classes and their behavior.
"""

from pathlib import Path

from src.domain.models import (
    AppFlowyPackage,
    NotionPackage,
    OutlinePackage,
    ProseMirrorDocument,
    TransformedContent,
    VaultStructure,
)


class TestVaultStructure:
    """Test suite for VaultStructure data class."""

    def test_vault_structure_creation_with_all_fields(self):
        """Test that VaultStructure can be created with all required fields."""
        # Given: Valid data for all fields
        path = Path("/test/vault")
        markdown_files = [Path("note1.md"), Path("note2.md")]
        asset_files = [Path("image.png")]
        links = {"note1": ["note2"]}
        metadata = {"note1": {"title": "Note 1"}}

        # When: We create a VaultStructure
        vault = VaultStructure(
            path=path,
            markdown_files=markdown_files,
            asset_files=asset_files,
            links=links,
            metadata=metadata,
        )

        # Then: All fields should be set correctly
        assert vault.path == path
        assert vault.markdown_files == markdown_files
        assert vault.asset_files == asset_files
        assert vault.links == links
        assert vault.metadata == metadata

    def test_vault_structure_is_immutable(self):
        """Test that VaultStructure is immutable (frozen dataclass)."""
        # Given: A VaultStructure instance
        vault = VaultStructure(
            path=Path("/test"),
            markdown_files=[],
            asset_files=[],
            links={},
            metadata={},
        )

        # When/Then: Attempting to modify any field should raise an error
        try:
            vault.path = Path("/other")
            raise AssertionError("Should not be able to modify frozen dataclass")
        except AttributeError:
            pass  # Expected behavior


class TestTransformedContent:
    """Test suite for TransformedContent data class."""

    def test_transformed_content_creation_with_all_fields(self):
        """Test that TransformedContent can be created with all required fields."""
        # Given: Valid data for all fields
        original_path = Path("original.md")
        markdown = "# Transformed Content"
        metadata = {"title": "Test"}
        assets = [Path("image.png")]
        warnings = ["Warning 1"]

        # When: We create a TransformedContent
        content = TransformedContent(
            original_path=original_path,
            markdown=markdown,
            metadata=metadata,
            assets=assets,
            warnings=warnings,
        )

        # Then: All fields should be set correctly
        assert content.original_path == original_path
        assert content.markdown == markdown
        assert content.metadata == metadata
        assert content.assets == assets
        assert content.warnings == warnings

    def test_transformed_content_is_immutable(self):
        """Test that TransformedContent is immutable (frozen dataclass)."""
        # Given: A TransformedContent instance
        content = TransformedContent(
            original_path=Path("test.md"),
            markdown="# Test",
            metadata={},
            assets=[],
            warnings=[],
        )

        # When/Then: Attempting to modify any field should raise an error
        try:
            content.markdown = "# Modified"
            raise AssertionError("Should not be able to modify frozen dataclass")
        except AttributeError:
            pass  # Expected behavior


class TestAppFlowyPackage:
    """Test suite for AppFlowyPackage data class."""

    def test_appflowy_package_creation_with_all_fields(self):
        """Test that AppFlowyPackage can be created with all required fields."""
        # Given: Valid data for all fields
        documents = [{"type": "page", "content": "test"}]
        assets = [Path("image.png")]
        config = {"version": "1.0"}
        warnings = ["Warning 1"]

        # When: We create an AppFlowyPackage
        package = AppFlowyPackage(
            documents=documents, assets=assets, config=config, warnings=warnings
        )

        # Then: All fields should be set correctly
        assert package.documents == documents
        assert package.assets == assets
        assert package.config == config
        assert package.warnings == warnings

    def test_appflowy_package_is_immutable(self):
        """Test that AppFlowyPackage is immutable (frozen dataclass)."""
        # Given: An AppFlowyPackage instance
        package = AppFlowyPackage(documents=[], assets=[], config={}, warnings=[])

        # When/Then: Attempting to modify any field should raise an error
        try:
            package.documents = [{"modified": True}]
            raise AssertionError("Should not be able to modify frozen dataclass")
        except AttributeError:
            pass  # Expected behavior


class TestNotionPackage:
    """Test suite for NotionPackage data class."""

    def test_notion_package_creation_with_all_fields(self):
        """Test that NotionPackage can be created with all required fields."""
        # Given: Valid data for all fields
        documents = [
            {"name": "page.md", "content": "# Page Content", "path": "page.md"}
        ]
        assets = [Path("image.png")]
        warnings = ["Warning 1"]

        # When: We create a NotionPackage
        package = NotionPackage(documents=documents, assets=assets, warnings=warnings)

        # Then: All fields should be set correctly
        assert package.documents == documents
        assert package.assets == assets
        assert package.warnings == warnings

    def test_notion_package_no_config_field(self):
        """Test that NotionPackage doesn't have a config field (unlike AppFlowyPackage)."""
        # Given: A NotionPackage instance
        package = NotionPackage(documents=[], assets=[], warnings=[])

        # When/Then: NotionPackage should not have a config attribute
        assert not hasattr(package, "config")

    def test_notion_package_is_immutable(self):
        """Test that NotionPackage is immutable (frozen dataclass)."""
        # Given: A NotionPackage instance
        package = NotionPackage(documents=[], assets=[], warnings=[])

        # When/Then: Attempting to modify any field should raise an error
        try:
            package.documents = [{"modified": True}]
            raise AssertionError("Should not be able to modify frozen dataclass")
        except AttributeError:
            pass  # Expected behavior

    def test_notion_package_empty_creation(self):
        """Test that NotionPackage can be created with empty collections."""
        # When: We create an empty NotionPackage
        package = NotionPackage(documents=[], assets=[], warnings=[])

        # Then: All fields should be empty but present
        assert package.documents == []
        assert package.assets == []
        assert package.warnings == []


class TestOutlinePackage:
    """Test suite for OutlinePackage data class."""

    def test_outline_package_creation_with_all_fields(self):
        """Test that OutlinePackage can be created with all required fields."""
        # Given: Valid data for all fields following Outline JSON format
        metadata = {
            "exportVersion": 1,
            "version": "0.78.0-0",
            "createdAt": "2024-07-18T18:18:14.221Z",
            "createdById": "user-uuid",
            "createdByEmail": "user@example.com",
        }
        collections = [
            {
                "id": "collection-uuid",
                "urlId": "short-id",
                "name": "Test Collection",
                "data": {"type": "doc", "content": []},
                "documentStructure": [],
            }
        ]
        documents = {
            "doc-uuid": {
                "id": "doc-uuid",
                "title": "Test Document",
                "data": {"type": "doc", "content": []},
                "createdAt": "2024-07-18T18:03:41.622Z",
            }
        }
        attachments = {
            "attachment-uuid": {
                "id": "attachment-uuid",
                "documentId": "doc-uuid",
                "contentType": "image/jpeg",
                "name": "test.jpg",
                "key": "uploads/test.jpg",
            }
        }
        warnings = ["Test warning"]

        # When: We create an OutlinePackage
        package = OutlinePackage(
            metadata=metadata,
            collections=collections,
            documents=documents,
            attachments=attachments,
            warnings=warnings,
        )

        # Then: All fields should be set correctly
        assert package.metadata == metadata
        assert package.collections == collections
        assert package.documents == documents
        assert package.attachments == attachments
        assert package.warnings == warnings

    def test_outline_package_is_immutable(self):
        """Test that OutlinePackage is immutable (frozen dataclass)."""
        # Given: An OutlinePackage instance
        package = OutlinePackage(
            metadata={},
            collections=[],
            documents={},
            attachments={},
            warnings=[],
        )

        # When/Then: Attempting to modify any field should raise an error
        try:
            package.metadata = {"modified": True}
            raise AssertionError("Should not be able to modify frozen dataclass")
        except AttributeError:
            pass  # Expected behavior

    def test_outline_package_empty_creation(self):
        """Test that OutlinePackage can be created with empty collections."""
        # When: We create an empty OutlinePackage
        package = OutlinePackage(
            metadata={},
            collections=[],
            documents={},
            attachments={},
            warnings=[],
        )

        # Then: All fields should be empty but present
        assert package.metadata == {}
        assert package.collections == []
        assert package.documents == {}
        assert package.attachments == {}
        assert package.warnings == []


class TestProseMirrorDocument:
    """Test suite for ProseMirrorDocument data class."""

    def test_prosemirror_document_creation_with_all_fields(self):
        """Test that ProseMirrorDocument can be created with all required fields."""
        # Given: Valid ProseMirror document structure
        doc_type = "doc"
        content = [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Hello world"}],
            }
        ]
        attrs = {"title": "Test Document"}

        # When: We create a ProseMirrorDocument
        doc = ProseMirrorDocument(type=doc_type, content=content, attrs=attrs)

        # Then: All fields should be set correctly
        assert doc.type == doc_type
        assert doc.content == content
        assert doc.attrs == attrs

    def test_prosemirror_document_minimal_creation(self):
        """Test that ProseMirrorDocument can be created with minimal required fields."""
        # Given: Minimal valid data (only type and content required)
        doc_type = "doc"
        content = []

        # When: We create a minimal ProseMirrorDocument
        doc = ProseMirrorDocument(type=doc_type, content=content)

        # Then: Required fields should be set, optional ones should default
        assert doc.type == doc_type
        assert doc.content == content
        assert doc.attrs is None

    def test_prosemirror_document_is_immutable(self):
        """Test that ProseMirrorDocument is immutable (frozen dataclass)."""
        # Given: A ProseMirrorDocument instance
        doc = ProseMirrorDocument(type="doc", content=[])

        # When/Then: Attempting to modify any field should raise an error
        try:
            doc.type = "paragraph"
            raise AssertionError("Should not be able to modify frozen dataclass")
        except AttributeError:
            pass  # Expected behavior

    def test_prosemirror_document_empty_content(self):
        """Test that ProseMirrorDocument can handle empty content arrays."""
        # When: We create a ProseMirrorDocument with empty content
        doc = ProseMirrorDocument(type="doc", content=[])

        # Then: Content should be empty but present
        assert doc.content == []
        assert isinstance(doc.content, list)
