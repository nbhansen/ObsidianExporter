"""
Test cases for NotionPackageGenerator.

Following CLAUDE.md TDD approach: RED → GREEN → REFACTOR
These tests validate the exact Notion ZIP package format that AppFlowy expects.

CRITICAL: All tests verify the precise ZIP structure, file naming, and content
requirements for successful AppFlowy web import.
"""

import tempfile
import zipfile
from pathlib import Path

from src.domain.models import NotionPackage
from src.infrastructure.generators.notion_package_generator import (
    NotionPackageGenerator,
)


class TestNotionPackageGenerator:
    """Test suite validating EXACT Notion ZIP package generation."""

    def test_create_notion_package_generator(self):
        """
        Test creating NotionPackageGenerator.

        Should initialize without external dependencies following hexagonal
        architecture.
        """
        generator = NotionPackageGenerator()

        assert generator is not None

    def test_generate_notion_zip_package_exact_structure(self):
        """
        Test generating Notion ZIP with EXACT structure AppFlowy expects.

        CRITICAL: ZIP must contain markdown files with exact naming format.
        No config.json or documents/ directory - just markdown files directly.
        """
        generator = NotionPackageGenerator()

        # Given: NotionPackage with exact format documents
        notion_documents = [
            {
                "name": "My Page 6db51a77742b4b11bedb1f0e02e27af8.md",
                "content": "# My Page\n\nThis is page content.\n",
                "path": "My Page 6db51a77742b4b11bedb1f0e02e27af8.md",
            },
            {
                "name": "Nested Page abc123def456789012345678901234567.md",
                "content": "# Nested Page\n\nNested content.\n",
                "path": "Parent Dir abc123def456789012345678901234567/Nested Page abc123def456789012345678901234567.md",
            },
        ]

        package = NotionPackage(documents=notion_documents, assets=[], warnings=[])

        # When: Generate ZIP package
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "notion_export.zip"
            result_path = generator.generate_package(package, output_path)

            # Then: ZIP must exist and be valid
            assert result_path.exists()
            assert zipfile.is_zipfile(result_path)

            # Validate exact ZIP structure
            with zipfile.ZipFile(result_path, "r") as zf:
                files = zf.namelist()

                # Should contain markdown files directly (no documents/ directory)
                assert "My Page 6db51a77742b4b11bedb1f0e02e27af8.md" in files
                assert (
                    "Parent Dir abc123def456789012345678901234567/Nested Page abc123def456789012345678901234567.md"
                    in files
                )

                # Should NOT contain config.json (Notion format doesn't use it)
                assert "config.json" not in files

                # Validate content matches exactly
                content1 = zf.read(
                    "My Page 6db51a77742b4b11bedb1f0e02e27af8.md"
                ).decode("utf-8")
                assert content1 == "# My Page\n\nThis is page content.\n"

    def test_generate_package_with_assets_exact_paths(self):
        """
        Test asset handling with EXACT path structure.

        CRITICAL: Assets must be placed in same directory as referencing page
        with URL-encoded directory names.
        """
        generator = NotionPackageGenerator()

        # Given: Package with assets
        test_asset = Path("test_image.png")
        notion_documents = [
            {
                "name": "Image Page 1234567890abcdef1234567890abcdef.md",
                "content": "# Image Page\n\n![Test](Image%20Page%201234567890abcdef1234567890abcdef/test_image.png)\n",
                "path": "Image Page 1234567890abcdef1234567890abcdef.md",
            }
        ]

        package = NotionPackage(
            documents=notion_documents, assets=[test_asset], warnings=[]
        )

        # Create temporary asset file
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_path = Path(temp_dir) / "test_image.png"
            asset_path.write_bytes(b"fake_png_data")
            package = NotionPackage(
                documents=notion_documents, assets=[asset_path], warnings=[]
            )

            output_path = Path(temp_dir) / "notion_with_assets.zip"
            result_path = generator.generate_package(package, output_path)

            # Then: Assets should be in correct directory structure
            with zipfile.ZipFile(result_path, "r") as zf:
                files = zf.namelist()

                # Asset should be in page directory (URL-decoded for ZIP structure)
                expected_asset_path = (
                    "Image Page 1234567890abcdef1234567890abcdef/test_image.png"
                )
                assert expected_asset_path in files

    def test_generate_empty_package_gracefully(self):
        """
        Test generating package with no documents.

        Should create valid empty ZIP without errors.
        """
        generator = NotionPackageGenerator()

        # Given: Empty NotionPackage
        package = NotionPackage(documents=[], assets=[], warnings=[])

        # When: Generate ZIP package
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "empty_notion.zip"
            result_path = generator.generate_package(package, output_path)

            # Then: Should create valid but empty ZIP
            assert result_path.exists()
            assert zipfile.is_zipfile(result_path)

            with zipfile.ZipFile(result_path, "r") as zf:
                files = zf.namelist()
                # May contain warnings.txt if warnings present, otherwise empty
                assert len(files) == 0

    def test_include_warnings_when_present(self):
        """
        Test that warnings are included in ZIP package.

        Should add warnings.txt file with all warning messages.
        """
        generator = NotionPackageGenerator()

        # Given: Package with warnings
        package = NotionPackage(
            documents=[],
            assets=[],
            warnings=["Warning 1: Wikilink not resolved", "Warning 2: Image not found"],
        )

        # When: Generate ZIP package
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "notion_with_warnings.zip"
            result_path = generator.generate_package(package, output_path)

            # Then: Should include warnings.txt
            with zipfile.ZipFile(result_path, "r") as zf:
                files = zf.namelist()
                assert "warnings.txt" in files

                warnings_content = zf.read("warnings.txt").decode("utf-8")
                assert "Warning 1: Wikilink not resolved" in warnings_content
                assert "Warning 2: Image not found" in warnings_content

    def test_validate_notion_package_structure(self):
        """
        Test package validation for Notion format.

        Should validate that ZIP contains proper Notion structure.
        """
        generator = NotionPackageGenerator()

        # Given: Valid Notion package
        notion_documents = [
            {
                "name": "Test Page abcdef1234567890abcdef1234567890.md",
                "content": "# Test\n",
                "path": "Test Page abcdef1234567890abcdef1234567890.md",
            }
        ]
        package = NotionPackage(documents=notion_documents, assets=[], warnings=[])

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "valid_notion.zip"
            generator.generate_package(package, output_path)

            # When: Validate package
            is_valid = generator.validate_package(output_path)

            # Then: Should be valid
            assert is_valid

    def test_reject_invalid_zip_files(self):
        """
        Test validation rejects invalid ZIP files.

        Should return False for non-ZIP or malformed files.
        """
        generator = NotionPackageGenerator()

        # Given: Invalid file (not a ZIP)
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "invalid.zip"
            invalid_path.write_text("This is not a ZIP file")

            # When: Validate invalid file
            is_valid = generator.validate_package(invalid_path)

            # Then: Should be invalid
            assert not is_valid

    def test_handle_duplicate_filenames_in_zip(self):
        """
        Test handling of duplicate filenames in ZIP.

        Should generate unique paths for documents with same names.
        """
        generator = NotionPackageGenerator()

        # Given: Documents that would create duplicate ZIP paths
        notion_documents = [
            {
                "name": "Same Name 1234567890abcdef1234567890abcdef.md",
                "content": "# First Version\n",
                "path": "Same Name 1234567890abcdef1234567890abcdef.md",
            },
            {
                "name": "Same Name abcdef1234567890abcdef1234567890.md",
                "content": "# Second Version\n",
                "path": "Same Name abcdef1234567890abcdef1234567890.md",
            },
        ]
        package = NotionPackage(documents=notion_documents, assets=[], warnings=[])

        # When: Generate package
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "duplicate_names.zip"
            result_path = generator.generate_package(package, output_path)

            # Then: Should handle duplicates without overwriting
            with zipfile.ZipFile(result_path, "r") as zf:
                files = zf.namelist()
                # Both documents should exist (different IDs make them unique)
                assert len([f for f in files if f.endswith(".md")]) == 2

    def test_preserve_directory_structure_exactly(self):
        """
        Test that nested directory structure is preserved exactly.

        CRITICAL: Must maintain exact path structure from document paths.
        """
        generator = NotionPackageGenerator()

        # Given: Nested document structure
        notion_documents = [
            {
                "name": "Root Page 1111111111111111111111111111111.md",
                "content": "# Root\n",
                "path": "Root Page 1111111111111111111111111111111.md",
            },
            {
                "name": "Child Page 2222222222222222222222222222222.md",
                "content": "# Child\n",
                "path": "Root Page 1111111111111111111111111111111/Child Page 2222222222222222222222222222222.md",
            },
            {
                "name": "Grandchild 3333333333333333333333333333333.md",
                "content": "# Grandchild\n",
                "path": "Root Page 1111111111111111111111111111111/Child Page 2222222222222222222222222222222/Grandchild 3333333333333333333333333333333.md",
            },
        ]
        package = NotionPackage(documents=notion_documents, assets=[], warnings=[])

        # When: Generate package
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested_structure.zip"
            result_path = generator.generate_package(package, output_path)

            # Then: Directory structure should be preserved exactly
            with zipfile.ZipFile(result_path, "r") as zf:
                files = zf.namelist()

                assert "Root Page 1111111111111111111111111111111.md" in files
                assert (
                    "Root Page 1111111111111111111111111111111/Child Page 2222222222222222222222222222222.md"
                    in files
                )
                assert (
                    "Root Page 1111111111111111111111111111111/Child Page 2222222222222222222222222222222/Grandchild 3333333333333333333333333333333.md"
                    in files
                )
