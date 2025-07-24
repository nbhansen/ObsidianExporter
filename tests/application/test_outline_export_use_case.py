"""
Test cases for OutlineExportUseCase.

These tests validate the complete Outline export pipeline orchestration.
"""

from pathlib import Path
from unittest.mock import Mock

from src.application.outline_export_use_case import (
    OutlineExportConfig,
    OutlineExportUseCase,
)
from src.domain.content_transformer import ContentTransformer
from src.domain.models import (
    OutlinePackage,
    TransformedContent,
    VaultIndex,
    VaultStructure,
)
from src.domain.outline_document_generator import OutlineDocumentGenerator
from src.domain.vault_analyzer import VaultAnalyzer
from src.domain.vault_index_builder import VaultIndexBuilder
from src.infrastructure.file_system import FileSystemAdapter
from src.infrastructure.generators.outline_package_generator import (
    OutlinePackageGenerator,
)


class TestOutlineExportUseCase:
    """Test suite for OutlineExportUseCase."""

    def setup_method(self):
        """Set up test fixtures with mocked dependencies."""
        # Create mocked dependencies
        self.vault_analyzer = Mock(spec=VaultAnalyzer)
        self.vault_index_builder = Mock(spec=VaultIndexBuilder)
        self.content_transformer = Mock(spec=ContentTransformer)
        self.outline_document_generator = Mock(spec=OutlineDocumentGenerator)
        self.outline_package_generator = Mock(spec=OutlinePackageGenerator)
        self.file_system = Mock(spec=FileSystemAdapter)

        # Create use case with injected dependencies
        self.use_case = OutlineExportUseCase(
            vault_analyzer=self.vault_analyzer,
            vault_index_builder=self.vault_index_builder,
            content_transformer=self.content_transformer,
            outline_document_generator=self.outline_document_generator,
            outline_package_generator=self.outline_package_generator,
            file_system=self.file_system,
        )

    def test_successful_export(self):
        """Test complete successful export pipeline."""
        # Given: Valid export configuration
        vault_path = Path("/test/vault")
        output_path = Path("/test/output.zip")
        config = OutlineExportConfig(
            vault_path=vault_path,
            output_path=output_path,
            package_name="Test Vault",
        )

        # Mock vault structure
        vault_structure = VaultStructure(
            path=vault_path,
            markdown_files=[Path("test.md")],
            asset_files=[Path("image.png")],
            links={"test": ["other"]},
            metadata={"test": {"title": "Test"}},
        )
        self.vault_analyzer.scan_vault.return_value = vault_structure

        # Mock vault index
        vault_index = VaultIndex(
            vault_path=vault_path,
            files_by_name={"test": Path("test.md")},
            all_paths={"test.md": Path("test.md")},
        )
        self.vault_index_builder.build_index.return_value = vault_index

        # Mock file system
        self.file_system.read_file_content.return_value = "# Test Content"

        # Mock content transformation
        transformed_content = TransformedContent(
            original_path=Path("test.md"),
            markdown="# Test Content",
            metadata={"title": "Test"},
            assets=[Path("image.png")],
            warnings=[],
        )
        self.content_transformer.transform_content.return_value = transformed_content

        # Mock Outline package generation
        outline_package = OutlinePackage(
            metadata={"exportVersion": 1},
            collections=[{"id": "test-id", "name": "Test Vault"}],
            documents={"doc-id": {"title": "Test"}},
            attachments={},
            warnings=[],
        )
        self.outline_document_generator.generate_outline_package.return_value = (
            outline_package
        )

        # Mock ZIP generation
        self.outline_package_generator.generate_package.return_value = output_path

        # When: We execute the export
        result = self.use_case.export(config)

        # Then: Export should succeed
        assert result.success is True
        assert result.output_path == output_path
        assert result.files_processed == 1
        assert result.assets_processed == 1
        assert len(result.errors) == 0

        # Verify all dependencies were called correctly
        self.vault_analyzer.scan_vault.assert_called_once_with(vault_path)
        self.vault_index_builder.build_index.assert_called_once_with(vault_path)
        self.content_transformer.transform_content.assert_called_once()
        self.outline_document_generator.generate_outline_package.assert_called_once()
        self.outline_package_generator.generate_package.assert_called_once()

    def test_export_with_multiple_files(self):
        """Test export with multiple markdown files."""
        # Given: Configuration with multiple files
        config = OutlineExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/test/output.zip"),
            package_name="Multi Vault",
        )

        # Mock vault structure with multiple files
        vault_structure = VaultStructure(
            path=Path("/test/vault"),
            markdown_files=[Path("doc1.md"), Path("doc2.md"), Path("doc3.md")],
            asset_files=[],
            links={},
            metadata={},
        )
        self.vault_analyzer.scan_vault.return_value = vault_structure

        # Mock other dependencies
        self.vault_index_builder.build_index.return_value = Mock()
        self.file_system.read_file_content.return_value = "# Content"

        # Mock content transformation for each file
        def mock_transform(file_path, content, index):
            return TransformedContent(
                original_path=file_path,
                markdown=content,
                metadata={},
                assets=[],
                warnings=[],
            )

        self.content_transformer.transform_content.side_effect = mock_transform

        # Mock Outline generation with proper structure
        mock_outline_package = Mock()
        mock_outline_package.attachments = {}
        self.outline_document_generator.generate_outline_package.return_value = (
            mock_outline_package
        )
        self.outline_package_generator.generate_package.return_value = Path(
            "/test/output.zip"
        )

        # When: We execute the export
        result = self.use_case.export(config)

        # Then: All files should be processed
        assert result.success is True
        assert result.files_processed == 3
        assert self.content_transformer.transform_content.call_count == 3

    def test_export_with_warnings(self):
        """Test export preserves warnings from content transformation."""
        # Given: Configuration
        config = OutlineExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/test/output.zip"),
            package_name="Warning Vault",
        )

        # Mock vault structure
        vault_structure = VaultStructure(
            path=Path("/test/vault"),
            markdown_files=[Path("problem.md")],
            asset_files=[],
            links={},
            metadata={},
        )
        self.vault_analyzer.scan_vault.return_value = vault_structure

        # Mock dependencies
        self.vault_index_builder.build_index.return_value = Mock()
        self.file_system.read_file_content.return_value = "# Content"

        # Mock content transformation with warnings
        transformed_content = TransformedContent(
            original_path=Path("problem.md"),
            markdown="# Content",
            metadata={},
            assets=[],
            warnings=["Broken link found", "Invalid syntax"],
        )
        self.content_transformer.transform_content.return_value = transformed_content

        # Mock other dependencies
        mock_outline_package = Mock()
        mock_outline_package.attachments = {}
        self.outline_document_generator.generate_outline_package.return_value = (
            mock_outline_package
        )
        self.outline_package_generator.generate_package.return_value = Path(
            "/test/output.zip"
        )

        # When: We execute the export
        result = self.use_case.export(config)

        # Then: Warnings should be preserved
        assert result.success is True
        assert len(result.warnings) == 2
        assert "Broken link found" in result.warnings
        assert "Invalid syntax" in result.warnings

    def test_export_handles_file_read_errors(self):
        """Test export handles file reading errors gracefully."""
        # Given: Configuration
        config = OutlineExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/test/output.zip"),
            package_name="Error Vault",
        )

        # Mock vault structure
        vault_structure = VaultStructure(
            path=Path("/test/vault"),
            markdown_files=[Path("readable.md"), Path("unreadable.md")],
            asset_files=[],
            links={},
            metadata={},
        )
        self.vault_analyzer.scan_vault.return_value = vault_structure

        # Mock dependencies
        self.vault_index_builder.build_index.return_value = Mock()

        # Mock file system with error for second file
        def mock_read_file(file_path):
            if file_path.name == "unreadable.md":
                raise OSError("Permission denied")
            return "# Content"

        self.file_system.read_file_content.side_effect = mock_read_file

        # Mock successful transformation for readable file
        transformed_content = TransformedContent(
            original_path=Path("readable.md"),
            markdown="# Content",
            metadata={},
            assets=[],
            warnings=[],
        )
        self.content_transformer.transform_content.return_value = transformed_content

        # Mock other dependencies
        mock_outline_package = Mock()
        mock_outline_package.attachments = {}
        self.outline_document_generator.generate_outline_package.return_value = (
            mock_outline_package
        )
        self.outline_package_generator.generate_package.return_value = Path(
            "/test/output.zip"
        )

        # When: We execute the export
        result = self.use_case.export(config)

        # Then: Should handle error gracefully
        assert result.success is False  # Has errors
        assert result.files_processed == 1  # Only readable file processed
        assert len(result.errors) == 1
        assert "unreadable.md" in result.errors[0]
        assert "Permission denied" in result.errors[0]

    def test_validate_only_mode(self):
        """Test validate-only mode doesn't create ZIP file."""
        # Given: Configuration with validate_only=True
        config = OutlineExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/test/output.zip"),
            package_name="Validate Vault",
            validate_only=True,
        )

        # Mock dependencies
        self.vault_analyzer.scan_vault.return_value = Mock()
        self.vault_index_builder.build_index.return_value = Mock()
        self.file_system.read_file_content.return_value = "# Content"
        self.content_transformer.transform_content.return_value = Mock()
        mock_outline_package = Mock()
        mock_outline_package.attachments = {}
        self.outline_document_generator.generate_outline_package.return_value = (
            mock_outline_package
        )

        # When: We execute the validation
        result = self.use_case.export(config)

        # Then: ZIP generator should not be called
        self.outline_package_generator.generate_package.assert_not_called()
        assert result.output_path is None

    def test_progress_callback(self):
        """Test progress reporting via callback."""
        # Given: Configuration with progress callback
        progress_messages = []

        def capture_progress(message):
            progress_messages.append(message)

        config = OutlineExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/test/output.zip"),
            package_name="Progress Vault",
            progress_callback=capture_progress,
        )

        # Mock minimal dependencies for successful run
        self.vault_analyzer.scan_vault.return_value = Mock(
            markdown_files=[Path("test.md")], asset_files=[]
        )
        self.vault_index_builder.build_index.return_value = Mock()
        self.file_system.read_file_content.return_value = "# Test"
        self.content_transformer.transform_content.return_value = Mock(
            warnings=[], assets=[]
        )
        mock_outline_package = Mock()
        mock_outline_package.attachments = {}
        self.outline_document_generator.generate_outline_package.return_value = (
            mock_outline_package
        )
        self.outline_package_generator.generate_package.return_value = Path(
            "/test/output.zip"
        )

        # When: We execute the export
        result = self.use_case.export(config)

        # Then: Progress messages should be captured
        assert len(progress_messages) > 0
        assert any("Analyzing vault structure" in msg for msg in progress_messages)
        # Test that at least one progress message was called - exact messages may vary
        # This ensures the progress callback mechanism works

    def test_vault_info_generation(self):
        """Test vault info generation in result."""
        # Given: Configuration
        config = OutlineExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/test/output.zip"),
            package_name="Info Vault",
        )

        # Mock vault structure with various files
        vault_structure = VaultStructure(
            path=Path("/test/vault"),
            markdown_files=[Path("doc1.md"), Path("doc2.md")],
            asset_files=[Path("img1.png"), Path("img2.jpg"), Path("doc.pdf")],
            links={"doc1": ["doc2"], "doc2": ["doc1"]},
            metadata={"doc1": {"title": "Doc 1"}, "doc2": {"author": "Test"}},
        )
        self.vault_analyzer.scan_vault.return_value = vault_structure

        # Mock other dependencies
        self.vault_index_builder.build_index.return_value = Mock()
        self.file_system.read_file_content.return_value = "# Content"
        self.content_transformer.transform_content.return_value = Mock(warnings=[])
        mock_outline_package = Mock()
        mock_outline_package.attachments = {}
        self.outline_document_generator.generate_outline_package.return_value = (
            mock_outline_package
        )
        self.outline_package_generator.generate_package.return_value = Path(
            "/test/output.zip"
        )

        # When: We execute the export
        result = self.use_case.export(config)

        # Then: Vault info should be populated
        assert result.vault_info is not None
        assert result.vault_info["markdown_files"] == 2
        assert result.vault_info["asset_files"] == 3
        assert result.vault_info["total_links"] == 2  # doc1->doc2, doc2->doc1
        assert result.vault_info["files_with_metadata"] == 2
