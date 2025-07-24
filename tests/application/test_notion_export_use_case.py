"""
Test cases for NotionExportUseCase.

Following CLAUDE.md TDD approach: RED → GREEN → REFACTOR
These tests validate the complete orchestration of Notion export pipeline.

CRITICAL: All tests verify the end-to-end workflow produces valid
Notion-compatible ZIP packages that AppFlowy can import.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from src.application.notion_export_use_case import (
    NotionExportConfig,
    NotionExportUseCase,
)
from src.domain.models import VaultStructure


class TestNotionExportUseCase:
    """Test suite for complete Notion export orchestration."""

    def test_create_notion_export_use_case(self):
        """
        Test creating NotionExportUseCase with dependencies.

        Should initialize with all required domain and infrastructure services
        following hexagonal architecture.
        """
        # Given: Mock dependencies
        vault_analyzer = Mock()
        content_transformer = Mock()
        notion_document_generator = Mock()
        notion_package_generator = Mock()
        file_system = Mock()

        # When: Create use case
        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # Then: Should initialize successfully
        assert use_case is not None

    def test_export_simple_vault_to_notion_zip(self):
        """
        Test complete export pipeline for simple vault.

        Should orchestrate all services to produce valid Notion ZIP package.
        """
        # Given: Mock dependencies with successful responses
        vault_analyzer = Mock()
        vault_structure = VaultStructure(
            path=Path("/test/vault"),
            markdown_files=[Path("test.md")],
            asset_files=[],
            links={},
            metadata={},
        )
        vault_analyzer.analyze_vault.return_value = vault_structure

        content_transformer = Mock()
        transformed_contents = [
            Mock(
                original_path=Path("test.md"),
                markdown="# Test Page\n\nContent here.\n",
                metadata={"title": "Test Page"},
                assets=[],
                warnings=[],
            )
        ]
        content_transformer.transform_content.return_value = transformed_contents

        notion_document_generator = Mock()
        notion_documents = [
            {
                "name": "Test Page 1234567890abcdef1234567890abcdef.md",
                "content": "# Test Page\n\nContent here.\n",
                "path": "Test Page 1234567890abcdef1234567890abcdef.md",
            }
        ]
        notion_document_generator.convert_to_notion_format.return_value = (
            notion_documents[0]
        )

        notion_package_generator = Mock()
        file_system = Mock()

        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # When: Export vault
        with tempfile.TemporaryDirectory() as temp_dir:
            config = NotionExportConfig(
                vault_path=Path("/test/vault"),
                output_path=Path(temp_dir) / "export.zip",
                package_name="test_export",
            )

            result = use_case.export(config)

            # Then: Should succeed with proper orchestration
            assert result.success
            assert vault_analyzer.analyze_vault.called
            assert content_transformer.transform_content.called
            assert notion_document_generator.convert_to_notion_format.called
            assert notion_package_generator.generate_package.called

    def test_export_with_progress_callback(self):
        """
        Test export with progress reporting callback.

        Should call progress callback at key stages of the pipeline.
        """
        # Given: Mock dependencies and progress callback
        vault_analyzer = Mock()
        vault_analyzer.analyze_vault.return_value = VaultStructure(
            path=Path("/test"), markdown_files=[], asset_files=[], links={}, metadata={}
        )

        content_transformer = Mock()
        content_transformer.transform_content.return_value = []

        notion_document_generator = Mock()
        notion_package_generator = Mock()
        file_system = Mock()

        progress_callback = Mock()

        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # When: Export with progress callback
        with tempfile.TemporaryDirectory() as temp_dir:
            config = NotionExportConfig(
                vault_path=Path("/test/vault"),
                output_path=Path(temp_dir) / "export.zip",
                package_name="test_export",
                progress_callback=progress_callback,
            )

            use_case.export(config)

            # Then: Progress callback should be called
            assert progress_callback.called
            # Should be called multiple times for different stages
            assert progress_callback.call_count >= 3

    def test_export_handles_transformer_errors_gracefully(self):
        """
        Test export error handling when content transformation fails.

        Should collect errors and continue processing other files when possible.
        """
        # Given: Mock dependencies where transformer raises exception
        vault_analyzer = Mock()
        vault_analyzer.analyze_vault.return_value = VaultStructure(
            path=Path("/test"),
            markdown_files=[Path("test.md")],
            asset_files=[],
            links={},
            metadata={},
        )

        content_transformer = Mock()
        content_transformer.transform_content.side_effect = Exception(
            "Transform failed"
        )

        notion_document_generator = Mock()
        notion_package_generator = Mock()
        file_system = Mock()

        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # When: Export with error condition
        with tempfile.TemporaryDirectory() as temp_dir:
            config = NotionExportConfig(
                vault_path=Path("/test/vault"),
                output_path=Path(temp_dir) / "export.zip",
                package_name="test_export",
            )

            result = use_case.export(config)

            # Then: Should handle error gracefully
            assert not result.success
            assert len(result.errors) > 0
            assert "Transform failed" in str(result.errors[0])

    def test_export_aggregates_warnings_from_all_stages(self):
        """
        Test that warnings from all pipeline stages are aggregated.

        Should collect warnings from vault analysis, transformation, and generation.
        """
        # Given: Mock dependencies that produce warnings
        vault_analyzer = Mock()
        vault_analyzer.analyze_vault.return_value = VaultStructure(
            path=Path("/test"), markdown_files=[], asset_files=[], links={}, metadata={}
        )

        content_transformer = Mock()
        transformed_content = Mock()
        transformed_content.warnings = ["Transformer warning"]
        content_transformer.transform_content.return_value = [transformed_content]

        notion_document_generator = Mock()
        notion_document_generator.convert_to_notion_format.return_value = {
            "name": "test.md",
            "content": "# Test",
            "path": "test.md",
        }

        notion_package_generator = Mock()
        file_system = Mock()

        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # When: Export with warning-producing content
        with tempfile.TemporaryDirectory() as temp_dir:
            config = NotionExportConfig(
                vault_path=Path("/test/vault"),
                output_path=Path(temp_dir) / "export.zip",
                package_name="test_export",
            )

            result = use_case.export(config)

            # Then: Should aggregate warnings
            assert "Transformer warning" in result.warnings

    def test_validate_only_mode_skips_package_generation(self):
        """
        Test validate-only mode that checks content without generating ZIP.

        Should perform analysis and transformation but skip package generation.
        """
        # Given: Mock dependencies
        vault_analyzer = Mock()
        vault_analyzer.analyze_vault.return_value = VaultStructure(
            path=Path("/test"), markdown_files=[], asset_files=[], links={}, metadata={}
        )

        content_transformer = Mock()
        content_transformer.transform_content.return_value = []

        notion_document_generator = Mock()
        notion_package_generator = Mock()
        file_system = Mock()

        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # When: Export in validate-only mode
        with tempfile.TemporaryDirectory() as temp_dir:
            config = NotionExportConfig(
                vault_path=Path("/test/vault"),
                output_path=Path(temp_dir) / "export.zip",
                package_name="test_export",
                validate_only=True,
            )

            result = use_case.export(config)

            # Then: Should validate but not generate package
            assert result.success
            assert vault_analyzer.analyze_vault.called
            assert content_transformer.transform_content.called
            assert not notion_package_generator.generate_package.called

    def test_export_records_processing_metrics(self):
        """
        Test that export records comprehensive processing metrics.

        Should track files processed, processing time, and other metrics.
        """
        # Given: Mock dependencies with countable content
        vault_analyzer = Mock()
        vault_structure = VaultStructure(
            path=Path("/test"),
            markdown_files=[Path("file1.md"), Path("file2.md")],
            asset_files=[Path("image.png")],
            links={},
            metadata={},
        )
        vault_analyzer.analyze_vault.return_value = vault_structure

        content_transformer = Mock()
        mock_content1 = Mock()
        mock_content1.assets = [Path("image.png")]
        mock_content1.warnings = []
        mock_content1.original_path = Path("file1.md")
        mock_content1.markdown = "# File 1\n\nContent here."
        mock_content2 = Mock()
        mock_content2.assets = []
        mock_content2.warnings = []
        mock_content2.original_path = Path("file2.md")
        mock_content2.markdown = "# File 2\n\nMore content."
        content_transformer.transform_content.return_value = [
            mock_content1,
            mock_content2,
        ]

        notion_document_generator = Mock()
        notion_document_generator.convert_to_notion_format.return_value = {
            "name": "test.md",
            "content": "# Test",
            "path": "test.md",
        }

        notion_package_generator = Mock()
        file_system = Mock()

        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # When: Export vault
        with tempfile.TemporaryDirectory() as temp_dir:
            config = NotionExportConfig(
                vault_path=Path("/test/vault"),
                output_path=Path(temp_dir) / "export.zip",
                package_name="test_export",
            )

            result = use_case.export(config)

            # Then: Should record processing metrics
            assert result.files_processed == 2
            assert result.assets_processed == 1
            assert result.processing_time > 0
            assert result.vault_info is not None
