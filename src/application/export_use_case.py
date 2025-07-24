"""
Export use case for orchestrating complete vault-to-AppFlowy conversion.

This application service coordinates all domain services to perform
the complete export pipeline with progress reporting and error handling.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..domain.appflowy_document_generator import AppFlowyDocumentGenerator
from ..domain.content_transformer import ContentTransformer
from ..domain.models import AppFlowyPackage, VaultStructure
from ..domain.vault_analyzer import VaultAnalyzer
from ..domain.vault_index_builder import VaultIndexBuilder
from ..infrastructure.file_system import FileSystemAdapter
from ..infrastructure.generators.appflowy_package_generator import (
    AppFlowyPackageGenerator,
)


@dataclass
class ExportConfig:
    """Configuration for vault export operation."""

    vault_path: Path
    output_path: Path
    package_name: str
    progress_callback: Optional[Callable[[str], None]] = None
    validate_only: bool = False


@dataclass
class ExportResult:
    """Result of vault export operation with comprehensive metrics."""

    success: bool
    output_path: Optional[Path] = None
    files_processed: int = 0
    assets_processed: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    broken_links: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    vault_info: Optional[Dict[str, Any]] = None


class ExportUseCase:
    """
    Application service orchestrating complete vault export pipeline.

    Coordinates domain services to perform vault analysis, content transformation,
    document generation, and package creation with comprehensive error handling
    and progress reporting.
    """

    def __init__(
        self,
        vault_analyzer: VaultAnalyzer,
        content_transformer: ContentTransformer,
        document_generator: AppFlowyDocumentGenerator,
        package_generator: AppFlowyPackageGenerator,
        vault_index_builder: VaultIndexBuilder,
        file_system: FileSystemAdapter,
    ) -> None:
        """
        Initialize export use case with required domain services.

        Args:
            vault_analyzer: Service for vault structure analysis
            content_transformer: Service for markdown content transformation
            document_generator: Service for AppFlowy document generation
            package_generator: Service for ZIP package creation
            vault_index_builder: Service for building vault indices
            file_system: Service for file system operations
        """
        self.vault_analyzer = vault_analyzer
        self.content_transformer = content_transformer
        self.document_generator = document_generator
        self.package_generator = package_generator
        self.vault_index_builder = vault_index_builder
        self.file_system = file_system

    def export_vault(self, config: ExportConfig) -> ExportResult:
        """
        Execute complete vault export pipeline.

        Args:
            config: Export configuration with paths and options

        Returns:
            ExportResult with success status, metrics, and any errors
        """
        start_time = time.time()
        result = ExportResult(success=False)

        try:
            # Step 1: Analyze vault structure
            self._report_progress(config, "Scanning vault structure...")
            vault_structure = self.vault_analyzer.scan_vault(config.vault_path)

            result.vault_info = {
                "total_files": len(vault_structure.markdown_files),
                "total_assets": len(vault_structure.asset_files),
                "total_links": sum(
                    len(links) for links in vault_structure.links.values()
                ),
            }

            # Step 2: Detect broken links
            broken_links = self._detect_broken_links(vault_structure)
            result.broken_links = broken_links

            # If validation-only mode, return early
            if config.validate_only:
                result.success = True
                result.processing_time = time.time() - start_time
                return result

            # Step 3: Build vault index for wikilink resolution
            self._report_progress(config, "Building vault index...")
            vault_index = self.vault_index_builder.build_index(config.vault_path)

            # Step 4: Transform content for each file
            self._report_progress(config, "Transforming content...")
            transformed_contents = []
            all_warnings = []

            for md_file in vault_structure.markdown_files:
                try:
                    self._report_progress(config, f"Processing {md_file.name}...")
                    # Read file content
                    markdown_content = self.file_system.read_file_content(md_file)

                    # Transform content using new interface
                    transformed = self.content_transformer.transform_content(
                        md_file, markdown_content, vault_index
                    )
                    transformed_contents.append(transformed)
                    all_warnings.extend(transformed.warnings)
                    result.files_processed += 1

                except Exception as e:
                    error_msg = f"Failed to transform {md_file.name}: {str(e)}"
                    result.errors.append(error_msg)
                    continue

            # Step 5: Generate AppFlowy documents
            self._report_progress(config, "Generating AppFlowy documents...")
            appflowy_documents = []

            for transformed in transformed_contents:
                try:
                    document = self.document_generator.generate_document(transformed)
                    # Add filename for package generation
                    document["name"] = transformed.original_path.stem + ".json"
                    appflowy_documents.append(document)

                except Exception as e:
                    error_msg = (
                        f"Failed to generate document for "
                        f"{transformed.original_path.name}: {str(e)}"
                    )
                    result.errors.append(error_msg)
                    continue

            # Step 6: Collect all assets
            all_assets = []
            for transformed in transformed_contents:
                all_assets.extend(transformed.assets)
            # Also include assets from vault structure
            all_assets.extend(vault_structure.asset_files)
            result.assets_processed = len(set(all_assets))  # Unique assets

            # Step 7: Create AppFlowy package
            self._report_progress(config, "Generating package...")
            package = AppFlowyPackage(
                documents=appflowy_documents,
                assets=list(set(all_assets)),  # Remove duplicates
                config={
                    "name": config.package_name,
                    "description": (
                        f"Converted from Obsidian vault: {config.vault_path.name}"
                    ),
                    "version": "1.0",
                    "created_by": "ObsidianExporter",
                },
                warnings=all_warnings,
            )

            # Step 8: Generate ZIP package
            output_path = self.package_generator.generate_package(
                package, config.output_path
            )

            # Success!
            result.success = True
            result.output_path = output_path
            result.warnings = all_warnings

            self._report_progress(
                config,
                f"Export completed! Package created: {output_path}",
            )

        except Exception as e:
            result.errors.append(f"Export failed: {str(e)}")
            result.success = False

        finally:
            result.processing_time = time.time() - start_time

        return result

    def _detect_broken_links(self, vault_structure: VaultStructure) -> List[str]:
        """
        Detect broken wikilinks in vault structure.

        Args:
            vault_structure: Analyzed vault structure

        Returns:
            List of broken link descriptions
        """
        broken_links = []
        existing_files = {
            f.stem for f in vault_structure.markdown_files
        }  # Available note names

        for source_file, links in vault_structure.links.items():
            for link in links:
                # Simple check - does the target exist as a file?
                # This is a basic implementation; real implementation would
                # need to handle the full wikilink resolution logic
                link_target = link.split("|")[0].split("#")[0].split("^")[0]
                if link_target not in existing_files:
                    broken_links.append(f"{source_file} → {link}")

        return broken_links

    def _report_progress(self, config: ExportConfig, message: str) -> None:
        """
        Report progress using callback if provided.

        Args:
            config: Export configuration with optional progress callback
            message: Progress message to report
        """
        if config.progress_callback:
            config.progress_callback(message)
