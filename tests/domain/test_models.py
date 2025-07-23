"""
Test cases for domain models.

These tests validate the immutable data classes and their behavior.
"""

from pathlib import Path

from src.domain.models import AppFlowyPackage, TransformedContent, VaultStructure


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
