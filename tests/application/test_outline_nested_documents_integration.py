"""
Integration tests for nested documents support in Outline export use case.

Tests the end-to-end functionality of the nested documents feature
including CLI integration and configuration handling.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.application.outline_export_use_case import (
    OutlineExportConfig,
    OutlineExportUseCase,
)
from src.domain.models import (
    FolderStructure,
    OutlinePackage,
    TransformedContent,
    VaultStructureWithFolders,
)


class TestOutlineExportUseCaseNestedDocuments:
    """Test suite for OutlineExportUseCase with nested documents."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for OutlineExportUseCase."""
        return {
            "vault_analyzer": Mock(),
            "vault_index_builder": Mock(),
            "content_transformer": Mock(),
            "outline_document_generator": Mock(),
            "outline_package_generator": Mock(),
            "file_system": Mock(),
        }

    @pytest.fixture
    def sample_vault_structure(self):
        """Create sample vault structure with folders."""
        return VaultStructureWithFolders(
            path=Path("/test/vault"),
            root_folder=FolderStructure(
                path=Path("/test/vault"),
                name="vault",
                parent_path=None,
                child_folders=[
                    FolderStructure(
                        path=Path("/test/vault/folder1"),
                        name="folder1",
                        parent_path=Path("/test/vault"),
                        child_folders=[],
                        markdown_files=[Path("/test/vault/folder1/note1.md")],
                        level=1,
                    )
                ],
                markdown_files=[Path("/test/vault/root_note.md")],
                level=0,
            ),
            all_folders=[],
            markdown_files=[
                Path("/test/vault/root_note.md"),
                Path("/test/vault/folder1/note1.md"),
            ],
            asset_files=[],
            folder_mapping={},
            links={},
            metadata={},
        )

    @pytest.fixture
    def sample_transformed_contents(self):
        """Create sample transformed contents."""
        return [
            TransformedContent(
                original_path=Path("/test/vault/root_note.md"),
                markdown="# Root Note\n\nRoot content",
                metadata={"title": "Root Note"},
                assets=[],
                warnings=[],
            ),
            TransformedContent(
                original_path=Path("/test/vault/folder1/note1.md"),
                markdown="# Note 1\n\nFolder content",
                metadata={"title": "Note 1"},
                assets=[],
                warnings=[],
            ),
        ]

    def test_export_with_nested_documents_enabled(
        self, mock_dependencies, sample_vault_structure, sample_transformed_contents
    ):
        """Test export use case with nested documents enabled."""
        # Given: Use case with mocked dependencies
        use_case = OutlineExportUseCase(**mock_dependencies)

        # And: Mock vault analyzer returns folder structure
        mock_dependencies["vault_analyzer"].scan_vault_with_folders.return_value = (
            sample_vault_structure
        )

        # And: Mock file system returns content
        mock_dependencies["file_system"].read_file_content.side_effect = [
            "# Root Note\n\nRoot content",
            "# Note 1\n\nFolder content",
        ]

        # And: Mock outline generator returns package
        mock_package = OutlinePackage(
            metadata={}, collections=[], documents={}, attachments={}, warnings=[]
        )
        mock_dependencies[
            "outline_document_generator"
        ].generate_outline_package_with_nested_documents.return_value = mock_package

        # And: Mock package generator returns output path
        output_path = Path("/test/output.zip")
        mock_dependencies["outline_package_generator"].generate_package.return_value = (
            output_path
        )

        # And: Export config with nested documents enabled
        config = OutlineExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/test/output.zip"),
            package_name="Test Vault",
            nested_documents=True,
        )

        # When: We export the vault
        result = use_case.export(config)

        # Then: Should use nested documents generator method
        mock_dependencies[
            "outline_document_generator"
        ].generate_outline_package_with_nested_documents.assert_called_once()

        # And: Should not use regular folder generator method
        mock_dependencies[
            "outline_document_generator"
        ].generate_outline_package_with_folders.assert_not_called()

        # And: Should succeed
        assert result.success is True
        assert result.output_path == output_path

    def test_export_with_nested_documents_disabled(
        self, mock_dependencies, sample_vault_structure, sample_transformed_contents
    ):
        """Test export use case with nested documents disabled (default behavior)."""
        # Given: Use case with mocked dependencies
        use_case = OutlineExportUseCase(**mock_dependencies)

        # And: Mock vault analyzer returns folder structure
        mock_dependencies["vault_analyzer"].scan_vault_with_folders.return_value = (
            sample_vault_structure
        )

        # And: Mock file system returns content
        mock_dependencies["file_system"].read_file_content.side_effect = [
            "# Root Note\n\nRoot content",
            "# Note 1\n\nFolder content",
        ]

        # And: Mock outline generator returns package
        mock_package = OutlinePackage(
            metadata={}, collections=[], documents={}, attachments={}, warnings=[]
        )
        mock_dependencies[
            "outline_document_generator"
        ].generate_outline_package_with_folders.return_value = mock_package

        # And: Mock package generator returns output path
        output_path = Path("/test/output.zip")
        mock_dependencies["outline_package_generator"].generate_package.return_value = (
            output_path
        )

        # And: Export config with nested documents disabled
        config = OutlineExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/test/output.zip"),
            package_name="Test Vault",
            nested_documents=False,  # Explicitly disabled
        )

        # When: We export the vault
        result = use_case.export(config)

        # Then: Should use regular folder generator method
        mock_dependencies[
            "outline_document_generator"
        ].generate_outline_package_with_folders.assert_called_once()

        # And: Should not use nested documents generator method
        mock_dependencies[
            "outline_document_generator"
        ].generate_outline_package_with_nested_documents.assert_not_called()

        # And: Should succeed
        assert result.success is True
        assert result.output_path == output_path

    def test_export_config_default_nested_documents_false(self):
        """Test that OutlineExportConfig defaults nested_documents to False."""
        # Given: Config without explicit nested_documents setting
        config = OutlineExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/test/output.zip"),
            package_name="Test Vault",
        )

        # Then: Should default to False
        assert config.nested_documents is False

    def test_export_passes_folder_structure_to_nested_generator(
        self, mock_dependencies, sample_vault_structure
    ):
        """Test that folder structure is correctly passed to nested documents generator."""
        # Given: Use case with mocked dependencies
        use_case = OutlineExportUseCase(**mock_dependencies)

        # And: Mock vault analyzer returns specific folder structure
        mock_dependencies["vault_analyzer"].scan_vault_with_folders.return_value = (
            sample_vault_structure
        )

        # And: Mock file system returns content
        mock_dependencies["file_system"].read_file_content.return_value = "# Test"

        # And: Mock outline generator returns package
        mock_package = OutlinePackage(
            metadata={}, collections=[], documents={}, attachments={}, warnings=[]
        )
        mock_dependencies[
            "outline_document_generator"
        ].generate_outline_package_with_nested_documents.return_value = mock_package

        # And: Export config with nested documents enabled
        config = OutlineExportConfig(
            vault_path=Path("/test/vault"),
            output_path=Path("/test/output.zip"),
            package_name="Test Vault",
            nested_documents=True,
        )

        # When: We export the vault
        use_case.export(config)

        # Then: Should pass the root folder structure to generator
        call_args = mock_dependencies[
            "outline_document_generator"
        ].generate_outline_package_with_nested_documents.call_args

        # Extract the folder_structure argument (third positional argument)
        passed_folder_structure = call_args[0][2]
        assert passed_folder_structure == sample_vault_structure.root_folder
        assert passed_folder_structure.name == "vault"
        assert len(passed_folder_structure.child_folders) == 1
        assert passed_folder_structure.child_folders[0].name == "folder1"
