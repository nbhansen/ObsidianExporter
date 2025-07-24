"""
Outline export use case for orchestrating complete vault-to-Outline conversion.

This application service coordinates all domain services to perform
the complete Outline export pipeline with progress reporting and error handling.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..domain.content_transformer import ContentTransformer
from ..domain.models import OutlinePackage, TransformedContent, VaultStructure
from ..domain.outline_document_generator import OutlineDocumentGenerator
from ..domain.vault_analyzer import VaultAnalyzer
from ..domain.vault_index_builder import VaultIndexBuilder
from ..infrastructure.file_system import FileSystemAdapter
from ..infrastructure.generators.outline_package_generator import (
    OutlinePackageGenerator,
)


@dataclass
class OutlineExportConfig:
    """Configuration for vault-to-Outline export operation."""

    vault_path: Path
    output_path: Path
    package_name: str
    progress_callback: Optional[Callable[[str], None]] = None
    validate_only: bool = False


@dataclass
class OutlineExportResult:
    """Result of vault-to-Outline export operation with comprehensive metrics."""

    success: bool
    output_path: Optional[Path] = None
    files_processed: int = 0
    assets_processed: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    broken_links: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    vault_info: Optional[Dict[str, Any]] = None


class OutlineExportUseCase:
    """
    Application service orchestrating complete vault-to-Outline export.

    Coordinates vault analysis, content transformation, Outline document generation,
    and ZIP package creation following hexagonal architecture principles.

    All dependencies are injected to maintain testability and separation of concerns.
    """

    def __init__(
        self,
        vault_analyzer: VaultAnalyzer,
        vault_index_builder: VaultIndexBuilder,
        content_transformer: ContentTransformer,
        outline_document_generator: OutlineDocumentGenerator,
        outline_package_generator: OutlinePackageGenerator,
        file_system: FileSystemAdapter,
    ):
        """
        Initialize use case with injected dependencies.

        Args:
            vault_analyzer: Domain service for vault structure analysis
            vault_index_builder: Domain service for building vault index
            content_transformer: Domain service for content transformation
            outline_document_generator: Domain service for Outline format generation
            outline_package_generator: Infrastructure service for ZIP creation
            file_system: Infrastructure adapter for file operations
        """
        self._vault_analyzer = vault_analyzer
        self._vault_index_builder = vault_index_builder
        self._content_transformer = content_transformer
        self._outline_document_generator = outline_document_generator
        self._outline_package_generator = outline_package_generator
        self._file_system = file_system

    def export(self, config: OutlineExportConfig) -> OutlineExportResult:
        """
        Execute complete vault-to-Outline export pipeline.

        Args:
            config: Export configuration with paths and options

        Returns:
            Comprehensive result with metrics, warnings, and errors
        """
        start_time = time.time()
        result = OutlineExportResult(success=False)

        try:
            # Stage 1: Analyze vault structure
            self._report_progress(config, "Analyzing vault structure...")
            vault_structure = self._vault_analyzer.scan_vault(config.vault_path)
            result.vault_info = self._generate_vault_info(vault_structure)

            # Stage 2: Build vault index for wikilink resolution
            self._report_progress(config, "Building vault index...")
            vault_index = self._vault_index_builder.build_index(config.vault_path)

            # Stage 3: Prepare raw content for Outline export (skip content transformation)
            # The OutlineDocumentGenerator handles wikilink resolution directly
            self._report_progress(config, "Preparing content...")
            transformed_contents = []

            for md_file in vault_structure.markdown_files:
                try:
                    # Read raw file content without transformation
                    markdown_content = self._file_system.read_file_content(md_file)

                    # Create minimal TransformedContent with raw markdown
                    # Wikilink resolution will be handled by OutlineDocumentGenerator
                    transformed = TransformedContent(
                        original_path=md_file,
                        markdown=markdown_content,
                        metadata={},  # Basic metadata - could extract frontmatter if needed
                        assets=[],    # Assets - could be collected if needed  
                        warnings=[]   # No warnings from transformation since we skip it
                    )
                    transformed_contents.append(transformed)

                except Exception as e:
                    error_msg = f"Failed to read {md_file.name}: {str(e)}"
                    result.errors.append(error_msg)
                    continue

            result.files_processed = len(transformed_contents)

            # Stage 4: Generate Outline format package
            self._report_progress(config, "Creating Outline package...")

            # Collect all assets
            all_assets = []
            for content in transformed_contents:
                all_assets.extend(content.assets)
            result.assets_processed = len(all_assets)

            # Create Outline package
            outline_package = self._outline_document_generator.generate_outline_package(
                transformed_contents, config.package_name
            )

            # Stage 5: Generate ZIP package (unless validate-only)
            if not config.validate_only:
                self._report_progress(config, "Creating Outline ZIP package...")

                # Create attachments mapping for assets
                attachments_mapping = self._create_attachments_mapping(
                    outline_package, all_assets
                )

                result.output_path = self._outline_package_generator.generate_package(
                    outline_package, config.output_path, attachments_mapping
                )

            result.success = len(result.errors) == 0
            result.processing_time = time.time() - start_time

            self._report_progress(
                config, f"Export completed in {result.processing_time:.2f}s"
            )

        except Exception as e:
            result.errors.append(f"Export pipeline failed: {str(e)}")
            result.processing_time = time.time() - start_time

        return result

    def validate(self, vault_path: Path) -> OutlineExportResult:
        """
        Validate vault can be exported to Outline format without creating package.

        Args:
            vault_path: Path to Obsidian vault

        Returns:
            Validation result with warnings and errors
        """
        config = OutlineExportConfig(
            vault_path=vault_path,
            output_path=Path("dummy.zip"),  # Not used in validate-only mode
            package_name="validation",
            validate_only=True,
        )

        return self.export(config)

    def _report_progress(self, config: OutlineExportConfig, message: str) -> None:
        """
        Report progress via callback if provided.

        Args:
            config: Export configuration with potential callback
            message: Progress message to report
        """
        if config.progress_callback:
            config.progress_callback(message)

    def _generate_vault_info(self, vault_structure: VaultStructure) -> Dict[str, Any]:
        """
        Generate summary information about vault structure.

        Args:
            vault_structure: Analyzed vault structure

        Returns:
            Dictionary with vault statistics and information
        """
        return {
            "vault_path": str(vault_structure.path),
            "markdown_files": len(vault_structure.markdown_files),
            "asset_files": len(vault_structure.asset_files),
            "total_links": sum(len(links) for links in vault_structure.links.values()),
            "files_with_metadata": len(vault_structure.metadata),
        }

    def _create_attachments_mapping(
        self, outline_package: OutlinePackage, assets: List[Path]
    ) -> Dict[str, Path]:
        """
        Create mapping between attachment IDs and file paths.

        Args:
            outline_package: Generated Outline package
            assets: List of asset file paths

        Returns:
            Dictionary mapping attachment IDs to file paths
        """
        mapping = {}

        # Create mapping based on attachment names and available assets
        for attachment_id, attachment in outline_package.attachments.items():
            attachment_name = attachment["name"]

            # Find matching asset by name
            for asset_path in assets:
                if asset_path.name == attachment_name:
                    mapping[attachment_id] = asset_path
                    break

        return mapping
