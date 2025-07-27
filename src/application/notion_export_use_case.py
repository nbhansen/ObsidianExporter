"""
Notion export use case for orchestrating complete vault-to-Notion conversion.

This application service coordinates all domain services to perform
the complete Notion export pipeline with progress reporting and error handling.

CRITICAL: Must produce exact Notion ZIP format that AppFlowy web import accepts.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..domain.content_transformer import ContentTransformer
from ..domain.models import NotionPackage, VaultStructure
from ..domain.notion_document_generator import NotionDocumentGenerator
from ..domain.vault_analyzer import VaultAnalyzer
from ..domain.vault_index_builder import VaultIndexBuilder
from ..infrastructure.file_system import FileSystemAdapter
from ..infrastructure.generators.notion_package_generator import NotionPackageGenerator


@dataclass
class NotionExportConfig:
    """Configuration for vault-to-Notion export operation."""

    vault_path: Path
    output_path: Path
    package_name: str
    progress_callback: Optional[Callable[[str], None]] = None
    validate_only: bool = False


@dataclass
class NotionExportResult:
    """Result of vault-to-Notion export operation with comprehensive metrics."""

    success: bool
    output_path: Optional[Path] = None
    files_processed: int = 0
    assets_processed: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    broken_links: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    vault_info: Optional[Dict[str, Any]] = None


class NotionExportUseCase:
    """
    Application service orchestrating complete vault-to-Notion export.

    Coordinates vault analysis, content transformation, Notion document generation,
    and ZIP package creation following hexagonal architecture principles.

    All dependencies are injected to maintain testability and separation of concerns.
    """

    def __init__(
        self,
        vault_analyzer: VaultAnalyzer,
        vault_index_builder: VaultIndexBuilder,
        content_transformer: ContentTransformer,
        notion_document_generator: NotionDocumentGenerator,
        notion_package_generator: NotionPackageGenerator,
        file_system: FileSystemAdapter,
    ):
        """
        Initialize use case with injected dependencies.

        Args:
            vault_analyzer: Domain service for vault structure analysis
            vault_index_builder: Domain service for building vault index
            content_transformer: Domain service for content transformation
            notion_document_generator: Domain service for Notion format generation
            notion_package_generator: Infrastructure service for ZIP creation
            file_system: Infrastructure adapter for file operations
        """
        self._vault_analyzer = vault_analyzer
        self._vault_index_builder = vault_index_builder
        self._content_transformer = content_transformer
        self._notion_document_generator = notion_document_generator
        self._notion_package_generator = notion_package_generator
        self._file_system = file_system

    def export(self, config: NotionExportConfig) -> NotionExportResult:
        """
        Execute complete vault-to-Notion export pipeline.

        Args:
            config: Export configuration with paths and options

        Returns:
            Comprehensive result with metrics, warnings, and errors
        """
        start_time = time.time()
        result = NotionExportResult(success=False)

        try:
            # Stage 1: Analyze vault structure
            self._report_progress(config, "Analyzing vault structure...")
            vault_structure = self._vault_analyzer.scan_vault(config.vault_path)
            result.vault_info = self._generate_vault_info(vault_structure)

            # Stage 2: Build vault index for wikilink resolution
            self._report_progress(config, "Building vault index...")
            vault_index = self._vault_index_builder.build_index(config.vault_path)

            # Stage 3: Transform content for each file
            self._report_progress(config, "Transforming content...")
            transformed_contents = []

            for md_file in vault_structure.markdown_files:
                try:
                    # Read file content
                    markdown_content = self._file_system.read_file_content(md_file)

                    # Transform content
                    transformed = self._content_transformer.transform_content(
                        md_file, markdown_content, vault_index
                    )
                    transformed_contents.append(transformed)
                    result.warnings.extend(transformed.warnings)

                except Exception as e:
                    error_msg = f"Failed to transform {md_file.name}: {str(e)}"
                    result.errors.append(error_msg)
                    continue

            result.files_processed = len(transformed_contents)

            # Stage 4: Generate Notion format documents
            self._report_progress(config, "Generating Notion format documents...")
            notion_documents = []

            for content in transformed_contents:
                try:
                    # Generate page name from file path
                    page_name = self._extract_page_name(content.original_path)

                    # Convert to AppFlowy JSON first (reusing existing logic)
                    appflowy_doc = self._create_appflowy_document(content)

                    # Convert to exact Notion format
                    notion_doc = (
                        self._notion_document_generator.convert_to_notion_format(
                            appflowy_doc, page_name
                        )
                    )
                    notion_documents.append(notion_doc)

                except Exception as e:
                    error_msg = (
                        f"Failed to generate Notion document for "
                        f"{content.original_path}: {str(e)}"
                    )
                    result.errors.append(error_msg)

            # Collect all assets
            all_assets = []
            for content in transformed_contents:
                all_assets.extend(content.assets)
            result.assets_processed = len(all_assets)

            # Create Notion package
            notion_package = NotionPackage(
                documents=notion_documents, assets=all_assets, warnings=result.warnings
            )

            # Stage 5: Generate ZIP package (unless validate-only)
            if not config.validate_only:
                self._report_progress(config, "Creating Notion ZIP package...")
                result.output_path = self._notion_package_generator.generate_package(
                    notion_package, config.output_path
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

    def validate(self, vault_path: Path) -> NotionExportResult:
        """
        Validate vault can be exported to Notion format without creating package.

        Args:
            vault_path: Path to Obsidian vault

        Returns:
            Validation result with warnings and errors
        """
        config = NotionExportConfig(
            vault_path=vault_path,
            output_path=Path("dummy.zip"),  # Not used in validate-only mode
            package_name="validation",
            validate_only=True,
        )

        return self.export(config)

    def _report_progress(self, config: NotionExportConfig, message: str) -> None:
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

    def _extract_page_name(self, file_path: Path) -> str:
        """
        Extract clean page name from file path.

        Args:
            file_path: Original markdown file path

        Returns:
            Clean page name for Notion format
        """
        # Use filename without extension as page name
        page_name = file_path.stem

        # Clean up common Obsidian naming patterns
        page_name = page_name.replace("_", " ")
        page_name = page_name.replace("-", " ")

        # Capitalize first letter of each word
        page_name = " ".join(word.capitalize() for word in page_name.split())

        return page_name

    def _create_appflowy_document(self, content: Any) -> Dict[str, Any]:
        """
        Create basic AppFlowy document structure from transformed content.

        Args:
            content: Transformed content with markdown and metadata

        Returns:
            AppFlowy document structure for Notion conversion
        """
        # Create simple document with paragraph content
        # This is a simplified approach - in full implementation, would need
        # proper markdown parsing to AppFlowy JSON conversion

        paragraphs = []

        # Split markdown into lines and create paragraph blocks
        lines = content.markdown.strip().split("\n")
        current_paragraph: List[str] = []

        for line in lines:
            line = line.strip()
            if not line:
                # Empty line - end current paragraph
                if current_paragraph:
                    text = " ".join(current_paragraph)
                    if text.startswith("# "):
                        # Heading level 1
                        paragraphs.append(
                            {
                                "type": "heading",
                                "data": {"delta": [{"insert": text[2:]}], "level": 1},
                            }
                        )
                    elif text.startswith("## "):
                        # Heading level 2
                        paragraphs.append(
                            {
                                "type": "heading",
                                "data": {"delta": [{"insert": text[3:]}], "level": 2},
                            }
                        )
                    else:
                        # Regular paragraph
                        paragraphs.append(
                            {"type": "paragraph", "data": {"delta": [{"insert": text}]}}
                        )
                    current_paragraph = []
            else:
                current_paragraph.append(line)

        # Handle remaining content
        if current_paragraph:
            text = " ".join(current_paragraph)
            if text.startswith("# "):
                paragraphs.append(
                    {
                        "type": "heading",
                        "data": {"delta": [{"insert": text[2:]}], "level": 1},
                    }
                )
            elif text.startswith("## "):
                paragraphs.append(
                    {
                        "type": "heading",
                        "data": {"delta": [{"insert": text[3:]}], "level": 2},
                    }
                )
            else:
                paragraphs.append(
                    {"type": "paragraph", "data": {"delta": [{"insert": text}]}}
                )

        return {"document": {"type": "page", "children": paragraphs}}
