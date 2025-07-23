"""
Test cases for export use case orchestration.

Following TDD approach - these tests define the expected behavior
for the complete vault export pipeline orchestration.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from src.application.export_use_case import ExportConfig, ExportResult, ExportUseCase
from src.domain.models import (
    TransformedContent,
    VaultIndex,
    VaultStructure,
)


class TestExportUseCase:
    """Test suite for ExportUseCase following TDD methodology."""

    def test_create_export_use_case(self):
        """
        Test creating export use case with dependencies.

        Should initialize with all required domain services.
        """
        vault_analyzer = Mock()
        content_transformer = Mock()
        document_generator = Mock()
        package_generator = Mock()
        vault_index_builder = Mock()
        file_system = Mock()

        use_case = ExportUseCase(
            vault_analyzer=vault_analyzer,
            content_transformer=content_transformer,
            document_generator=document_generator,
            package_generator=package_generator,
            vault_index_builder=vault_index_builder,
            file_system=file_system,
        )

        assert use_case is not None
        assert use_case.vault_analyzer == vault_analyzer
        assert use_case.content_transformer == content_transformer
        assert use_case.document_generator == document_generator
        assert use_case.package_generator == package_generator
        assert use_case.vault_index_builder == vault_index_builder
        assert use_case.file_system == file_system

    def test_export_vault_success(self):
        """
        Test successful vault export with complete pipeline.

        Should orchestrate all components and return success result.
        """
        # Mock dependencies
        vault_analyzer = Mock()
        content_transformer = Mock()
        document_generator = Mock()
        package_generator = Mock()
        vault_index_builder = Mock()
        file_system = Mock()

        # Mock vault analysis
        vault_structure = VaultStructure(
            path=Path("/test/vault"),
            markdown_files=[Path("/test/vault/note1.md"), Path("/test/vault/note2.md")],
            asset_files=[Path("/test/vault/image.png")],
            links={"note1": ["note2"]},
            metadata={"note1": {"title": "Note 1"}},
        )
        vault_analyzer.scan_vault.return_value = vault_structure

        # Mock vault index building
        vault_index = VaultIndex(
            vault_path=Path("/test/vault"),
            files_by_name={
                "note1": Path("/test/vault/note1.md"),
                "note2": Path("/test/vault/note2.md"),
            },
            all_paths={
                "note1.md": Path("/test/vault/note1.md"),
                "note2.md": Path("/test/vault/note2.md"),
            },
        )
        vault_index_builder.build_index.return_value = vault_index

        # Mock file system reads
        file_system.read_file_content.side_effect = [
            "# Note 1\nContent",
            "# Note 2\nMore content",
        ]

        # Mock content transformation
        transformed_contents = [
            TransformedContent(
                original_path=Path("/test/vault/note1.md"),
                markdown="# Note 1\nContent",
                metadata={"title": "Note 1"},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("/test/vault/note2.md"),
                markdown="# Note 2\nMore content",
                metadata={},
                assets=[Path("/test/vault/image.png")],
                warnings=["Sample warning"],
            ),
        ]
        content_transformer.transform_content.side_effect = transformed_contents

        # Mock document generation
        document_generator.generate_document.side_effect = [
            {"name": "note1.json", "document": {"type": "page", "children": []}},
            {"name": "note2.json", "document": {"type": "page", "children": []}},
        ]

        # Mock package generation
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "export.zip"
            package_generator.generate_package.return_value = output_path

            use_case = ExportUseCase(
                vault_analyzer=vault_analyzer,
                content_transformer=content_transformer,
                document_generator=document_generator,
                package_generator=package_generator,
                vault_index_builder=vault_index_builder,
                file_system=file_system,
            )

            config = ExportConfig(
                vault_path=Path("/test/vault"),
                output_path=output_path,
                package_name="Test Export",
            )

            result = use_case.export_vault(config)

            # Verify result
            assert isinstance(result, ExportResult)
            assert result.success is True
            assert result.output_path == output_path
            assert result.files_processed == 2
            assert result.warnings == ["Sample warning"]
            assert len(result.errors) == 0

            # Verify component calls
            vault_analyzer.scan_vault.assert_called_once_with(Path("/test/vault"))
            vault_index_builder.build_index.assert_called_once_with(Path("/test/vault"))
            assert file_system.read_file_content.call_count == 2
            file_system.read_file_content.assert_any_call(Path("/test/vault/note1.md"))
            file_system.read_file_content.assert_any_call(Path("/test/vault/note2.md"))
            assert content_transformer.transform_content.call_count == 2
            # Verify content_transformer was called with new interface
            content_transformer.transform_content.assert_any_call(
                Path("/test/vault/note1.md"), "# Note 1\nContent", vault_index
            )
            content_transformer.transform_content.assert_any_call(
                Path("/test/vault/note2.md"), "# Note 2\nMore content", vault_index
            )
            assert document_generator.generate_document.call_count == 2
            package_generator.generate_package.assert_called_once()

    def test_export_vault_with_progress_callback(self):
        """
        Test export with progress reporting callback.

        Should call progress callback at appropriate stages.
        """
        # Mock dependencies
        vault_analyzer = Mock()
        content_transformer = Mock()
        document_generator = Mock()
        package_generator = Mock()
        vault_index_builder = Mock()
        file_system = Mock()

        # Setup mocks
        vault_structure = VaultStructure(
            path=Path("/test/vault"),
            markdown_files=[Path("/test/vault/note.md")],
            asset_files=[],
            links={},
            metadata={},
        )
        vault_analyzer.scan_vault.return_value = vault_structure

        # Mock vault index building
        vault_index = VaultIndex(
            vault_path=Path("/test/vault"),
            files_by_name={"note": Path("/test/vault/note.md")},
            all_paths={"note.md": Path("/test/vault/note.md")},
        )
        vault_index_builder.build_index.return_value = vault_index

        # Mock file system read
        file_system.read_file_content.return_value = "# Note\nContent"

        transformed_content = TransformedContent(
            original_path=Path("/test/vault/note.md"),
            markdown="# Note\nContent",
            metadata={},
            assets=[],
            warnings=[],
        )
        content_transformer.transform_content.return_value = transformed_content

        document_generator.generate_document.return_value = {
            "name": "note.json",
            "document": {"type": "page", "children": []},
        }

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "export.zip"
            package_generator.generate_package.return_value = output_path

            use_case = ExportUseCase(
                vault_analyzer=vault_analyzer,
                content_transformer=content_transformer,
                document_generator=document_generator,
                package_generator=package_generator,
                vault_index_builder=vault_index_builder,
                file_system=file_system,
            )

            progress_callback = Mock()
            config = ExportConfig(
                vault_path=Path("/test/vault"),
                output_path=output_path,
                package_name="Test Export",
                progress_callback=progress_callback,
            )

            use_case.export_vault(config)

            # Verify progress callbacks were made
            # At least: scan, transform, generate
            assert progress_callback.call_count >= 3
            progress_calls = [call.args[0] for call in progress_callback.call_args_list]
            assert any("Scanning vault" in msg for msg in progress_calls)
            assert any("Transforming content" in msg for msg in progress_calls)
            assert any("Generating package" in msg for msg in progress_calls)

    def test_export_vault_with_transformation_errors(self):
        """
        Test export handling content transformation errors.

        Should continue processing and collect errors in result.
        """
        # Mock dependencies
        vault_analyzer = Mock()
        content_transformer = Mock()
        document_generator = Mock()
        package_generator = Mock()
        vault_index_builder = Mock()
        file_system = Mock()

        # Mock vault analysis
        vault_structure = VaultStructure(
            path=Path("/test/vault"),
            markdown_files=[Path("/test/vault/good.md"), Path("/test/vault/bad.md")],
            asset_files=[],
            links={},
            metadata={},
        )
        vault_analyzer.scan_vault.return_value = vault_structure

        # Mock vault index building
        vault_index = VaultIndex(
            vault_path=Path("/test/vault"),
            files_by_name={
                "good": Path("/test/vault/good.md"),
                "bad": Path("/test/vault/bad.md"),
            },
            all_paths={
                "good.md": Path("/test/vault/good.md"),
                "bad.md": Path("/test/vault/bad.md"),
            },
        )
        vault_index_builder.build_index.return_value = vault_index

        # Mock file system reads
        file_system.read_file_content.side_effect = [
            "# Good\nContent",
            "# Bad\nContent",
        ]

        # Mock content transformation - one success, one error
        good_content = TransformedContent(
            original_path=Path("/test/vault/good.md"),
            markdown="# Good\nContent",
            metadata={},
            assets=[],
            warnings=[],
        )
        content_transformer.transform_content.side_effect = [
            good_content,
            Exception("Transformation failed for bad.md"),
        ]

        # Mock document generation for successful content
        document_generator.generate_document.return_value = {
            "name": "good.json",
            "document": {"type": "page", "children": []},
        }

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "export.zip"
            package_generator.generate_package.return_value = output_path

            use_case = ExportUseCase(
                vault_analyzer=vault_analyzer,
                content_transformer=content_transformer,
                document_generator=document_generator,
                package_generator=package_generator,
                vault_index_builder=vault_index_builder,
                file_system=file_system,
            )

            config = ExportConfig(
                vault_path=Path("/test/vault"),
                output_path=output_path,
                package_name="Test Export",
            )

            result = use_case.export_vault(config)

            # Should still succeed but with errors recorded
            assert result.success is True  # Package was created
            assert result.files_processed == 1  # Only successful file
            assert len(result.errors) == 1
            assert "Transformation failed for bad.md" in result.errors[0]

    def test_export_vault_with_missing_vault(self):
        """
        Test export with non-existent vault path.

        Should return failure result with appropriate error.
        """
        vault_analyzer = Mock()
        vault_analyzer.scan_vault.side_effect = FileNotFoundError("Vault not found")

        use_case = ExportUseCase(
            vault_analyzer=vault_analyzer,
            content_transformer=Mock(),
            document_generator=Mock(),
            package_generator=Mock(),
            vault_index_builder=Mock(),
            file_system=Mock(),
        )

        config = ExportConfig(
            vault_path=Path("/nonexistent/vault"),
            output_path=Path("/tmp/export.zip"),
            package_name="Test Export",
        )

        result = use_case.export_vault(config)

        assert result.success is False
        assert result.files_processed == 0
        assert len(result.errors) == 1
        assert "Vault not found" in result.errors[0]

    def test_export_config_validation(self):
        """
        Test export configuration validation.

        Should validate required parameters and paths.
        """
        config = ExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/tmp/export.zip"),
            package_name="Test Export",
        )

        # Test required fields
        assert config.vault_path == Path("/test/vault")
        assert config.output_path == Path("/tmp/export.zip")
        assert config.package_name == "Test Export"

        # Test optional fields
        assert config.progress_callback is None
        assert config.validate_only is False

    def test_export_result_aggregation(self):
        """
        Test export result data aggregation.

        Should collect all metrics, warnings, and errors.
        """
        # Mock dependencies with various outcomes
        vault_analyzer = Mock()
        content_transformer = Mock()
        document_generator = Mock()
        package_generator = Mock()
        vault_index_builder = Mock()
        file_system = Mock()

        # Mock vault with multiple files
        vault_structure = VaultStructure(
            path=Path("/test/vault"),
            markdown_files=[
                Path("/test/vault/note1.md"),
                Path("/test/vault/note2.md"),
                Path("/test/vault/note3.md"),
            ],
            asset_files=[Path("/test/vault/image.png")],
            links={"note1": ["note2", "broken-link"]},
            metadata={},
        )
        vault_analyzer.scan_vault.return_value = vault_structure

        # Mock vault index building
        vault_index = VaultIndex(
            vault_path=Path("/test/vault"),
            files_by_name={
                "note1": Path("/test/vault/note1.md"),
                "note2": Path("/test/vault/note2.md"),
                "note3": Path("/test/vault/note3.md"),
            },
            all_paths={
                "note1.md": Path("/test/vault/note1.md"),
                "note2.md": Path("/test/vault/note2.md"),
                "note3.md": Path("/test/vault/note3.md"),
            },
        )
        vault_index_builder.build_index.return_value = vault_index

        # Mock file system reads
        file_system.read_file_content.side_effect = [
            "# Note 1",
            "# Note 2",
            "# Note 3",
        ]

        # Mock transformations with various warnings
        content_transformer.transform_content.side_effect = [
            TransformedContent(
                original_path=Path("/test/vault/note1.md"),
                markdown="# Note 1",
                metadata={},
                assets=[],
                warnings=["Warning 1", "Warning 2"],
            ),
            TransformedContent(
                original_path=Path("/test/vault/note2.md"),
                markdown="# Note 2",
                metadata={},
                assets=[],
                warnings=["Warning 3"],
            ),
            TransformedContent(
                original_path=Path("/test/vault/note3.md"),
                markdown="# Note 3",
                metadata={},
                assets=[],
                warnings=[],
            ),
        ]

        # Mock document generation
        document_generator.generate_document.side_effect = [
            {"name": "note1.json", "document": {"type": "page"}},
            {"name": "note2.json", "document": {"type": "page"}},
            {"name": "note3.json", "document": {"type": "page"}},
        ]

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "export.zip"
            package_generator.generate_package.return_value = output_path

            use_case = ExportUseCase(
                vault_analyzer=vault_analyzer,
                content_transformer=content_transformer,
                document_generator=document_generator,
                package_generator=package_generator,
                vault_index_builder=vault_index_builder,
                file_system=file_system,
            )

            config = ExportConfig(
                vault_path=Path("/test/vault"),
                output_path=output_path,
                package_name="Test Export",
            )

            result = use_case.export_vault(config)

            # Verify aggregated results
            assert result.success is True
            assert result.files_processed == 3
            assert len(result.warnings) == 3  # All warnings collected
            assert "Warning 1" in result.warnings
            assert "Warning 2" in result.warnings
            assert "Warning 3" in result.warnings
            assert result.assets_processed == 1

    def test_validate_only_mode(self):
        """
        Test validation-only mode without package generation.

        Should run validation and return results without creating package.
        """
        vault_analyzer = Mock()
        content_transformer = Mock()
        document_generator = Mock()
        package_generator = Mock()
        vault_index_builder = Mock()
        file_system = Mock()

        # Mock vault analysis
        vault_structure = VaultStructure(
            path=Path("/test/vault"),
            markdown_files=[Path("/test/vault/note.md")],
            asset_files=[],
            links={"note": ["broken-link"]},
            metadata={},
        )
        vault_analyzer.scan_vault.return_value = vault_structure

        use_case = ExportUseCase(
            vault_analyzer=vault_analyzer,
            content_transformer=content_transformer,
            document_generator=document_generator,
            package_generator=package_generator,
            vault_index_builder=vault_index_builder,
            file_system=file_system,
        )

        config = ExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/tmp/export.zip"),
            package_name="Test Export",
            validate_only=True,
        )

        result = use_case.export_vault(config)

        # Should validate but not generate package
        vault_analyzer.scan_vault.assert_called_once()
        vault_index_builder.build_index.assert_not_called()
        file_system.read_file_content.assert_not_called()
        content_transformer.transform_content.assert_not_called()
        document_generator.generate_document.assert_not_called()
        package_generator.generate_package.assert_not_called()

        # Should return validation results
        assert result.success is True
        assert result.output_path is None  # No package created
        assert len(result.broken_links) >= 1  # Should detect broken link
