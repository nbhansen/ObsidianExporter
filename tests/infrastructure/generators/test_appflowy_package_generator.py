"""
Test cases for AppFlowy package generator.

Following TDD approach - these tests define the expected behavior
for creating ZIP packages compatible with AppFlowy template import.
"""

import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from src.domain.models import AppFlowyPackage
from src.infrastructure.generators.appflowy_package_generator import (
    AppFlowyPackageGenerator,
)


class TestAppFlowyPackageGenerator:
    """Test suite for AppFlowyPackageGenerator following TDD methodology."""

    def test_create_package_generator(self):
        """
        Test creating AppFlowy package generator.

        Should initialize without dependencies.
        """
        generator = AppFlowyPackageGenerator()
        assert generator is not None

    def test_generate_empty_package(self):
        """
        Test generating empty AppFlowy package.

        Should create valid ZIP with minimal structure.
        """
        generator = AppFlowyPackageGenerator()

        package = AppFlowyPackage(
            documents=[],
            assets=[],
            config={"name": "Empty Package", "version": "1.0"},
            warnings=[],
        )

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "empty-package.zip"
            result_path = generator.generate_package(package, output_path)

            assert result_path == output_path
            assert output_path.exists()
            assert zipfile.is_zipfile(output_path)

            # Check ZIP contents
            with zipfile.ZipFile(output_path, "r") as zf:
                files = zf.namelist()
                assert "config.json" in files

    def test_generate_package_with_documents(self):
        """
        Test generating package with AppFlowy documents.

        Should include all documents in documents/ folder.
        """
        generator = AppFlowyPackageGenerator()

        documents = [
            {
                "name": "note1.json",
                "document": {
                    "type": "page",
                    "children": [
                        {
                            "type": "heading",
                            "data": {"level": 1, "delta": [{"insert": "Test Note"}]},
                        }
                    ],
                },
            },
            {
                "name": "note2.json",
                "document": {
                    "type": "page",
                    "children": [
                        {
                            "type": "paragraph",
                            "data": {"delta": [{"insert": "Another note"}]},
                        }
                    ],
                },
            },
        ]

        package = AppFlowyPackage(
            documents=documents,
            assets=[],
            config={"name": "Multi Document Package"},
            warnings=[],
        )

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "multi-doc.zip"
            generator.generate_package(package, output_path)

            # Verify ZIP structure
            with zipfile.ZipFile(output_path, "r") as zf:
                files = zf.namelist()
                assert "config.json" in files
                assert "documents/note1.json" in files
                assert "documents/note2.json" in files

                # Verify document content
                note1_content = json.loads(zf.read("documents/note1.json"))
                assert note1_content["document"]["type"] == "page"
                assert len(note1_content["document"]["children"]) == 1

    def test_generate_package_with_assets(self):
        """
        Test generating package with asset files.

        Should copy assets to assets/ folder with correct paths.
        """
        generator = AppFlowyPackageGenerator()

        # Create temporary asset files
        with TemporaryDirectory() as asset_dir:
            asset_path = Path(asset_dir)

            # Create test assets
            image_file = asset_path / "test-image.png"
            image_file.write_bytes(b"fake-png-data")

            doc_file = asset_path / "document.pdf"
            doc_file.write_bytes(b"fake-pdf-data")

            package = AppFlowyPackage(
                documents=[],
                assets=[image_file, doc_file],
                config={"name": "Asset Package"},
                warnings=[],
            )

            with TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir) / "assets.zip"
                generator.generate_package(package, output_path)

                # Verify assets in ZIP
                with zipfile.ZipFile(output_path, "r") as zf:
                    files = zf.namelist()
                    assert "assets/test-image.png" in files
                    assert "assets/document.pdf" in files

                    # Verify asset content
                    image_data = zf.read("assets/test-image.png")
                    assert image_data == b"fake-png-data"

    def test_generate_package_with_nested_assets(self):
        """
        Test generating package with nested asset directory structure.

        Should preserve folder structure in assets.
        """
        generator = AppFlowyPackageGenerator()

        with TemporaryDirectory() as asset_dir:
            asset_path = Path(asset_dir)

            # Create nested asset structure
            (asset_path / "images").mkdir()
            (asset_path / "docs").mkdir()

            img_file = asset_path / "images" / "nested.jpg"
            img_file.write_bytes(b"nested-image")

            pdf_file = asset_path / "docs" / "manual.pdf"
            pdf_file.write_bytes(b"nested-pdf")

            package = AppFlowyPackage(
                documents=[],
                assets=[img_file, pdf_file],
                config={"name": "Nested Assets"},
                warnings=[],
            )

            with TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir) / "nested.zip"
                generator.generate_package(package, output_path)

                with zipfile.ZipFile(output_path, "r") as zf:
                    files = zf.namelist()
                    # Should preserve relative paths
                    assert any("nested.jpg" in f for f in files)
                    assert any("manual.pdf" in f for f in files)

    def test_generate_config_json(self):
        """
        Test generating config.json manifest file.

        Should create proper AppFlowy template configuration.
        """
        generator = AppFlowyPackageGenerator()

        config = {
            "name": "My Obsidian Export",
            "description": "Converted from Obsidian vault",
            "version": "1.0",
            "author": "ObsidianExporter",
            "created": "2024-01-01T00:00:00Z",
        }

        # Test with package data
        package = AppFlowyPackage(
            documents=[{"name": "test.json", "document": {"type": "page"}}],
            assets=[],
            config=config,
            warnings=[],
        )

        result = generator._generate_config(config, package)

        assert result["name"] == "My Obsidian Export"
        assert result["description"] == "Converted from Obsidian vault"
        assert result["version"] == "1.0"
        assert "template_type" in result  # Should add template metadata
        assert "documents" in result  # Should include document list
        assert len(result["documents"]) == 1

    def test_calculate_package_paths(self):
        """
        Test calculating relative paths for package structure.

        Should handle various path scenarios correctly.
        """
        generator = AppFlowyPackageGenerator()

        # Test document paths
        doc_path = generator._get_document_path("my-note.json")
        assert doc_path == "documents/my-note.json"

        # Test asset paths
        asset_path = generator._get_asset_path(Path("images/photo.jpg"))
        assert "photo.jpg" in asset_path
        assert asset_path.startswith("assets/")

    def test_handle_file_conflicts(self):
        """
        Test handling of filename conflicts in package.

        Should rename conflicting files appropriately.
        """
        generator = AppFlowyPackageGenerator()

        documents = [
            {"name": "note.json", "document": {"type": "page", "children": []}},
            {
                "name": "note.json",
                "document": {"type": "page", "children": []},
            },  # Conflict
        ]

        package = AppFlowyPackage(
            documents=documents,
            assets=[],
            config={"name": "Conflict Test"},
            warnings=[],
        )

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "conflicts.zip"
            generator.generate_package(package, output_path)

            with zipfile.ZipFile(output_path, "r") as zf:
                files = zf.namelist()
                doc_files = [f for f in files if f.startswith("documents/")]
                assert len(doc_files) == 2  # Both files should be present
                assert len(set(doc_files)) == 2  # With different names

    def test_validate_package_structure(self):
        """
        Test validation of generated package structure.

        Should verify AppFlowy import compatibility.
        """
        generator = AppFlowyPackageGenerator()

        package = AppFlowyPackage(
            documents=[
                {"name": "test.json", "document": {"type": "page", "children": []}}
            ],
            assets=[],
            config={"name": "Validation Test"},
            warnings=[],
        )

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "validate.zip"
            generator.generate_package(package, output_path)

            # Validate package structure
            is_valid = generator.validate_package(output_path)
            assert is_valid is True

    def test_package_size_limits(self):
        """
        Test handling of large packages near size limits.

        Should handle large documents and many assets appropriately.
        """
        generator = AppFlowyPackageGenerator()

        # Create large document
        large_content = {"insert": "x" * 10000}  # Large content
        large_document = {
            "name": "large.json",
            "document": {
                "type": "page",
                "children": [{"type": "paragraph", "data": {"delta": [large_content]}}],
            },
        }

        package = AppFlowyPackage(
            documents=[large_document],
            assets=[],
            config={"name": "Large Package"},
            warnings=[],
        )

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "large.zip"
            generator.generate_package(package, output_path)

            assert output_path.exists()
            # Should handle large content without errors

    def test_preserve_warnings_in_package(self):
        """
        Test preserving conversion warnings in package metadata.

        Should include warnings in config or separate file.
        """
        generator = AppFlowyPackageGenerator()

        warnings = [
            "Broken link detected in note1.md",
            "Unknown callout type in note2.md",
            "Asset file missing: image.png",
        ]

        package = AppFlowyPackage(
            documents=[],
            assets=[],
            config={"name": "Warning Package"},
            warnings=warnings,
        )

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "warnings.zip"
            generator.generate_package(package, output_path)

            with zipfile.ZipFile(output_path, "r") as zf:
                files = zf.namelist()

                # Warnings should be preserved somewhere
                if "warnings.txt" in files:
                    warning_content = zf.read("warnings.txt").decode()
                    assert "Broken link detected" in warning_content
                else:
                    # Or in config.json
                    config_content = json.loads(zf.read("config.json"))
                    assert "warnings" in config_content

    def test_generate_package_with_custom_output_name(self):
        """
        Test generating package with custom output filename.

        Should respect provided output path and filename.
        """
        generator = AppFlowyPackageGenerator()

        package = AppFlowyPackage(
            documents=[], assets=[], config={"name": "Custom Name"}, warnings=[]
        )

        with TemporaryDirectory() as temp_dir:
            custom_path = Path(temp_dir) / "my-custom-export.zip"
            result_path = generator.generate_package(package, custom_path)

            assert result_path == custom_path
            assert custom_path.exists()
            assert custom_path.name == "my-custom-export.zip"

    def test_error_handling_invalid_package(self):
        """
        Test error handling for invalid package data.

        Should raise appropriate exceptions for malformed input.
        """
        generator = AppFlowyPackageGenerator()

        # Invalid package with malformed document
        invalid_package = AppFlowyPackage(
            documents=[{"invalid": "structure"}],  # Missing required fields
            assets=[],
            config={},  # Empty config
            warnings=[],
        )

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "invalid.zip"

            # Should handle gracefully or raise appropriate exception
            try:
                generator.generate_package(invalid_package, output_path)
                # If it doesn't raise, should still create some output
                assert output_path.exists()
            except (ValueError, KeyError) as e:
                # Expected for malformed input
                assert "invalid" in str(e).lower() or "missing" in str(e).lower()

    def test_zip_compression_settings(self):
        """
        Test ZIP compression settings for optimal file size.

        Should use appropriate compression for different file types.
        """
        generator = AppFlowyPackageGenerator()

        # Test that generator uses appropriate compression
        assert hasattr(generator, "_get_compression_type")

        # Text files should use deflate compression
        text_compression = generator._get_compression_type(".json")
        assert text_compression == zipfile.ZIP_DEFLATED

        # Binary files might use different compression
        binary_compression = generator._get_compression_type(".png")
        assert binary_compression in [zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED]
