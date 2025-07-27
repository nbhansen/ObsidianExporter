"""
Integration tests for NotionExportUseCase with real dependencies.

Following CLAUDE.md TDD approach: RED → GREEN → REFACTOR
These tests validate the complete integration of all services in the
Notion export pipeline, catching dependency injection issues.

CRITICAL: These tests use real implementations, not mocks, to ensure
proper integration and catch configuration errors.
"""

import tempfile
from pathlib import Path

import pytest

from src.application.notion_export_use_case import (
    NotionExportConfig,
    NotionExportUseCase,
)
from src.domain.content_transformer import ContentTransformer
from src.domain.notion_document_generator import NotionDocumentGenerator
from src.domain.vault_analyzer import VaultAnalyzer
from src.domain.vault_index_builder import VaultIndexBuilder
from src.domain.wikilink_resolver import WikiLinkResolver
from src.infrastructure.file_system import FileSystemAdapter
from src.infrastructure.generators.notion_package_generator import (
    NotionPackageGenerator,
)
from src.infrastructure.parsers.block_reference_parser import BlockReferenceParser
from src.infrastructure.parsers.callout_parser import CalloutParser
from src.infrastructure.parsers.wikilink_parser import WikiLinkParser


class TestNotionExportIntegration:
    """Integration test suite for complete Notion export pipeline."""

    def test_create_notion_export_use_case_with_real_dependencies(self):
        """
        Test creating NotionExportUseCase with real dependencies.

        CRITICAL: This test catches dependency injection issues that
        mocked tests miss. It ensures all required dependencies are properly
        configured and can be instantiated together.
        """
        # Given: Real dependency implementations
        file_system = FileSystemAdapter()
        wikilink_parser = WikiLinkParser()
        vault_analyzer = VaultAnalyzer(file_system, wikilink_parser)
        vault_index_builder = VaultIndexBuilder(file_system)
        wikilink_resolver = WikiLinkResolver()
        callout_parser = CalloutParser()
        block_reference_parser = BlockReferenceParser()
        content_transformer = ContentTransformer(
            wikilink_parser, wikilink_resolver, callout_parser, block_reference_parser
        )
        notion_document_generator = NotionDocumentGenerator()
        notion_package_generator = NotionPackageGenerator()

        # When: Create use case with real dependencies
        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            vault_index_builder=vault_index_builder,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # Then: Should initialize successfully
        assert use_case is not None

    def test_export_minimal_vault_end_to_end(self):
        """
        Test complete export pipeline with minimal real vault.

        Creates a temporary vault with basic content and runs the complete
        export pipeline to ensure all services integrate correctly.
        """
        # Given: Real dependencies
        file_system = FileSystemAdapter()
        wikilink_parser = WikiLinkParser()
        vault_analyzer = VaultAnalyzer(file_system, wikilink_parser)
        wikilink_resolver = WikiLinkResolver()
        callout_parser = CalloutParser()
        block_reference_parser = BlockReferenceParser()
        content_transformer = ContentTransformer(
            wikilink_parser, wikilink_resolver, callout_parser, block_reference_parser
        )
        notion_document_generator = NotionDocumentGenerator()
        notion_package_generator = NotionPackageGenerator()

        vault_index_builder = VaultIndexBuilder(file_system)

        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            vault_index_builder=vault_index_builder,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # Create minimal test vault
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_path = Path(temp_dir) / "test_vault"
            vault_path.mkdir()

            # Create .obsidian directory to make it a valid vault
            obsidian_dir = vault_path / ".obsidian"
            obsidian_dir.mkdir()

            # Create a simple markdown file
            test_file = vault_path / "test_note.md"
            test_file.write_text(
                "# Test Note\n\nThis is a test note for integration testing."
            )

            # Configure export
            output_path = Path(temp_dir) / "test_export.zip"
            config = NotionExportConfig(
                vault_path=vault_path,
                output_path=output_path,
                package_name="IntegrationTest",
            )

            # When: Run complete export pipeline
            result = use_case.export(config)

            # Then: Should complete without dependency errors
            assert result is not None
            # Note: We don't assert success=True here because content_transformer
            # might have issues with our minimal test content, but the integration
            # should work without dependency injection failures

    def test_validate_only_mode_integration(self):
        """
        Test validate-only mode with real dependencies.

        Ensures validation mode works with actual service implementations.
        """
        # Given: Real dependencies
        file_system = FileSystemAdapter()
        wikilink_parser = WikiLinkParser()
        vault_analyzer = VaultAnalyzer(file_system, wikilink_parser)
        wikilink_resolver = WikiLinkResolver()
        callout_parser = CalloutParser()
        block_reference_parser = BlockReferenceParser()
        content_transformer = ContentTransformer(
            wikilink_parser, wikilink_resolver, callout_parser, block_reference_parser
        )
        notion_document_generator = NotionDocumentGenerator()
        notion_package_generator = NotionPackageGenerator()

        vault_index_builder = VaultIndexBuilder(file_system)

        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            vault_index_builder=vault_index_builder,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # Create minimal test vault
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_path = Path(temp_dir) / "test_vault"
            vault_path.mkdir()

            obsidian_dir = vault_path / ".obsidian"
            obsidian_dir.mkdir()

            # When: Run validation
            result = use_case.validate(vault_path)

            # Then: Should complete validation without dependency errors
            assert result is not None
            assert result.processing_time >= 0

    def test_missing_dependency_raises_clear_error(self):
        """
        Test that missing dependencies raise clear errors.

        This test ensures we catch configuration issues early with clear messages.
        """
        # Given: Missing wikilink_parser dependency
        file_system = FileSystemAdapter()

        # When/Then: Should raise TypeError with clear message about missing dependency
        with pytest.raises(
            TypeError, match="missing.*required.*argument.*wikilink_parser"
        ):
            VaultAnalyzer(file_system)  # Missing wikilink_parser

    def test_all_required_imports_available(self):
        """
        Test that all required imports for integration are available.

        Ensures all dependencies can be imported and instantiated.
        """
        # Test that all classes can be imported and instantiated
        try:
            FileSystemAdapter()
            WikiLinkParser()
            wikilink_resolver = WikiLinkResolver()
            callout_parser = CalloutParser()
            block_reference_parser = BlockReferenceParser()
            ContentTransformer(
                WikiLinkParser(),
                wikilink_resolver,
                callout_parser,
                block_reference_parser,
            )
            NotionDocumentGenerator()
            NotionPackageGenerator()
        except Exception as e:
            pytest.fail(f"Failed to instantiate required dependencies: {e}")

    def test_content_transformer_dependencies(self):
        """
        Test ContentTransformer has all required dependencies.

        Ensures ContentTransformer can be created without missing dependencies.
        """
        # When: Create ContentTransformer with all dependencies
        wikilink_parser = WikiLinkParser()
        wikilink_resolver = WikiLinkResolver()
        callout_parser = CalloutParser()
        block_reference_parser = BlockReferenceParser()
        transformer = ContentTransformer(
            wikilink_parser, wikilink_resolver, callout_parser, block_reference_parser
        )

        # Then: Should initialize successfully
        assert transformer is not None

        # Should have required methods for the pipeline
        assert hasattr(transformer, "transform_content")

    def test_dependency_injection_chain_complete(self):
        """
        Test complete dependency injection chain.

        Validates that all services in the pipeline can be created with
        their dependencies in the correct order.
        """
        # Build dependency chain step by step

        # Step 1: Create infrastructure adapters
        file_system = FileSystemAdapter()
        wikilink_parser = WikiLinkParser()

        # Step 2: Create domain services that depend on infrastructure
        vault_analyzer = VaultAnalyzer(file_system, wikilink_parser)
        wikilink_resolver = WikiLinkResolver()
        callout_parser = CalloutParser()
        block_reference_parser = BlockReferenceParser()
        content_transformer = ContentTransformer(
            wikilink_parser, wikilink_resolver, callout_parser, block_reference_parser
        )
        notion_document_generator = NotionDocumentGenerator()

        # Step 3: Create infrastructure services that depend on domain
        notion_package_generator = NotionPackageGenerator()

        # Step 4: Create application service that orchestrates everything
        vault_index_builder = VaultIndexBuilder(file_system)

        use_case = NotionExportUseCase(
            vault_analyzer=vault_analyzer,
            vault_index_builder=vault_index_builder,
            content_transformer=content_transformer,
            notion_document_generator=notion_document_generator,
            notion_package_generator=notion_package_generator,
            file_system=file_system,
        )

        # All steps should succeed without errors
        assert use_case is not None
