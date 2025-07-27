"""
Click-based CLI interface for Obsidian to AppFlowy converter.

This module provides the command-line interface for converting Obsidian vaults
to AppFlowy-importable ZIP packages with progress reporting and validation.
"""

from pathlib import Path
from typing import Any, Optional, Union, cast

import click

from .application.export_use_case import ExportConfig, ExportUseCase
from .application.notion_export_use_case import NotionExportConfig, NotionExportUseCase
from .application.outline_export_use_case import (
    OutlineExportConfig,
    OutlineExportUseCase,
)
from .domain.appflowy_document_generator import AppFlowyDocumentGenerator
from .domain.content_transformer import ContentTransformer
from .domain.notion_document_generator import NotionDocumentGenerator
from .domain.outline_document_generator import OutlineDocumentGenerator
from .domain.vault_analyzer import VaultAnalyzer
from .domain.vault_index_builder import VaultIndexBuilder
from .domain.wikilink_resolver import WikiLinkResolver
from .infrastructure.file_system import FileSystemAdapter
from .infrastructure.generators.appflowy_package_generator import (
    AppFlowyPackageGenerator,
)
from .infrastructure.generators.notion_package_generator import NotionPackageGenerator
from .infrastructure.generators.outline_package_generator import OutlinePackageGenerator
from .infrastructure.parsers.block_reference_parser import BlockReferenceParser
from .infrastructure.parsers.callout_parser import CalloutParser
from .infrastructure.parsers.wikilink_parser import WikiLinkParser


def create_export_use_case() -> ExportUseCase:
    """
    Create export use case with all dependencies wired.

    Returns:
        Configured ExportUseCase with dependency injection
    """
    # Infrastructure adapters
    file_system = FileSystemAdapter()
    wikilink_parser = WikiLinkParser()
    callout_parser = CalloutParser()
    block_reference_parser = BlockReferenceParser()

    # Domain services
    vault_analyzer = VaultAnalyzer(
        file_system=file_system, wikilink_parser=wikilink_parser
    )
    vault_index_builder = VaultIndexBuilder(file_system=file_system)
    wikilink_resolver = WikiLinkResolver()
    content_transformer = ContentTransformer(
        wikilink_parser=wikilink_parser,
        wikilink_resolver=wikilink_resolver,
        callout_parser=callout_parser,
        block_reference_parser=block_reference_parser,
    )
    document_generator = AppFlowyDocumentGenerator()
    package_generator = AppFlowyPackageGenerator()

    return ExportUseCase(
        vault_analyzer=vault_analyzer,
        content_transformer=content_transformer,
        document_generator=document_generator,
        package_generator=package_generator,
        vault_index_builder=vault_index_builder,
        file_system=file_system,
    )


def create_notion_export_use_case() -> NotionExportUseCase:
    """
    Create Notion export use case with all dependencies wired.

    Returns:
        Configured NotionExportUseCase with dependency injection
    """
    # Infrastructure adapters
    file_system = FileSystemAdapter()
    wikilink_parser = WikiLinkParser()
    callout_parser = CalloutParser()
    block_reference_parser = BlockReferenceParser()

    # Domain services
    vault_analyzer = VaultAnalyzer(
        file_system=file_system, wikilink_parser=wikilink_parser
    )
    vault_index_builder = VaultIndexBuilder(file_system=file_system)
    wikilink_resolver = WikiLinkResolver()
    content_transformer = ContentTransformer(
        wikilink_parser=wikilink_parser,
        wikilink_resolver=wikilink_resolver,
        callout_parser=callout_parser,
        block_reference_parser=block_reference_parser,
    )
    notion_document_generator = NotionDocumentGenerator()
    notion_package_generator = NotionPackageGenerator()

    return NotionExportUseCase(
        vault_analyzer=vault_analyzer,
        vault_index_builder=vault_index_builder,
        content_transformer=content_transformer,
        notion_document_generator=notion_document_generator,
        notion_package_generator=notion_package_generator,
        file_system=file_system,
    )


def create_outline_export_use_case() -> OutlineExportUseCase:
    """
    Create outline export use case with all dependencies wired.

    Returns:
        Configured OutlineExportUseCase with dependency injection
    """
    # Infrastructure adapters
    file_system = FileSystemAdapter()
    wikilink_parser = WikiLinkParser()
    callout_parser = CalloutParser()
    block_reference_parser = BlockReferenceParser()

    # Domain services
    vault_analyzer = VaultAnalyzer(
        file_system=file_system, wikilink_parser=wikilink_parser
    )
    vault_index_builder = VaultIndexBuilder(file_system=file_system)
    wikilink_resolver = WikiLinkResolver()
    content_transformer = ContentTransformer(
        wikilink_parser=wikilink_parser,
        callout_parser=callout_parser,
        block_reference_parser=block_reference_parser,
        wikilink_resolver=wikilink_resolver,
    )
    outline_document_generator = OutlineDocumentGenerator()

    # Infrastructure generators
    outline_package_generator = OutlinePackageGenerator()

    return OutlineExportUseCase(
        vault_analyzer=vault_analyzer,
        vault_index_builder=vault_index_builder,
        content_transformer=content_transformer,
        outline_document_generator=outline_document_generator,
        outline_package_generator=outline_package_generator,
        file_system=file_system,
    )


@click.group()
@click.version_option(version="1.0.0", prog_name="obsidian-to-appflowy")
def cli() -> None:
    """
    Convert Obsidian vaults to AppFlowy, Notion, or Outline-importable packages.

    This tool converts Obsidian markdown vaults into ZIP packages that can be
    imported into AppFlowy (template format), AppFlowy via Notion import
    (Notion-compatible format), or Outline (JSON format), preserving content
    structure, wikilinks, and assets.
    """
    pass


@cli.command("convert")
@click.argument(
    "vault_path", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output path for the generated ZIP package",
)
@click.option(
    "--name",
    "-n",
    default=None,
    help="Name for the AppFlowy package (defaults to vault directory name)",
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed progress information"
)
@click.option(
    "--validate-only",
    is_flag=True,
    help="Only validate the vault without creating a package",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["appflowy", "notion", "outline"], case_sensitive=False),
    default="appflowy",
    help="Export format: 'appflowy', 'notion', or 'outline'",
)
def convert_command(
    vault_path: Path,
    output: Optional[Path],
    name: Optional[str],
    verbose: bool,
    validate_only: bool,
    format: str,
) -> None:
    """
    Convert an Obsidian vault to AppFlowy, Notion, or Outline package.

    VAULT_PATH: Path to the Obsidian vault directory to convert.

    Examples:
        obsidian-to-appflowy convert /path/to/vault
        obsidian-to-appflowy convert /path/to/vault --format notion
        obsidian-to-appflowy convert /path/to/vault --format outline
        obsidian-to-appflowy convert /path/to/vault --output my-export.zip -f outline
        obsidian-to-appflowy convert /path/to/vault --validate-only --format outline
    """
    # Validate inputs
    if not vault_path.exists():
        click.echo(f"Error: Vault path '{vault_path}' does not exist.", err=True)
        raise click.Abort()

    if not vault_path.is_dir():
        click.echo(f"Error: Vault path '{vault_path}' is not a directory.", err=True)
        raise click.Abort()

    # Set defaults
    if not name:
        name = vault_path.name

    if not output:
        if validate_only:
            # For validation, we don't need an actual output path
            output = Path("/tmp/validation-only")
        else:
            if format.lower() == "notion":
                format_suffix = "notion"
            elif format.lower() == "outline":
                format_suffix = "outline"
            else:
                format_suffix = "appflowy"
            output = Path.cwd() / f"{vault_path.name}-{format_suffix}-export.zip"

    if output and not validate_only:
        # Ensure output directory exists
        output.parent.mkdir(parents=True, exist_ok=True)

    # Create progress callback for verbose mode
    progress_callback = None
    if verbose:

        def progress_callback(message: str) -> None:
            click.echo(f"  {message}")

    try:
        # Create use case based on format choice
        use_case: Union[ExportUseCase, NotionExportUseCase, OutlineExportUseCase]
        config: Union[ExportConfig, NotionExportConfig, OutlineExportConfig]

        if format.lower() == "notion":
            use_case = create_notion_export_use_case()
            config = NotionExportConfig(
                vault_path=vault_path,
                output_path=output,
                package_name=name,
                progress_callback=progress_callback,
                validate_only=validate_only,
            )
        elif format.lower() == "outline":
            use_case = create_outline_export_use_case()
            config = OutlineExportConfig(
                vault_path=vault_path,
                output_path=output,
                package_name=name,
                progress_callback=progress_callback,
                validate_only=validate_only,
            )
        else:
            use_case = create_export_use_case()
            config = ExportConfig(
                vault_path=vault_path,
                output_path=output,
                package_name=name,
                progress_callback=progress_callback,
                validate_only=validate_only,
            )

        if verbose:
            mode = "validation" if validate_only else "conversion"
            format_name = format.capitalize()
            click.echo(f"Starting {format_name} {mode} of vault: {vault_path}")

        # Execute export with appropriate method
        result: Any  # Will hold Export/Notion/OutlineExportResult
        if format.lower() == "notion":
            notion_use_case = cast(NotionExportUseCase, use_case)
            notion_config = cast(NotionExportConfig, config)
            result = notion_use_case.export(notion_config)
        elif format.lower() == "outline":
            outline_use_case = cast(OutlineExportUseCase, use_case)
            outline_config = cast(OutlineExportConfig, config)
            result = outline_use_case.export(outline_config)
        else:
            appflowy_use_case = cast(ExportUseCase, use_case)
            appflowy_config = cast(ExportConfig, config)
            result = appflowy_use_case.export_vault(appflowy_config)

        # Display results
        if validate_only:
            _display_validation_results(result)
        else:
            _display_conversion_results(result)

        # Exit with appropriate code
        if not result.success:
            raise click.Abort()

    except Exception as e:
        mode = "validation" if validate_only else "conversion"
        click.echo(f"Error during {mode}: {str(e)}", err=True)
        raise click.Abort() from e


def _display_validation_results(result: Any) -> None:
    """Display validation results to user."""
    click.echo("\n" + "=" * 50)
    click.echo("VALIDATION RESULTS")
    click.echo("=" * 50)

    if result.vault_info:
        click.echo("📁 Vault structure:")
        click.echo(f"   Files: {result.vault_info.get('total_files', 0)}")
        click.echo(f"   Assets: {result.vault_info.get('total_assets', 0)}")
        click.echo(f"   Links: {result.vault_info.get('total_links', 0)}")

    if result.broken_links:
        click.echo(f"\n⚠️  {len(result.broken_links)} broken links found:")
        for link in result.broken_links[:10]:  # Show first 10
            click.echo(f"   • {link}")
        if len(result.broken_links) > 10:
            click.echo(f"   ... and {len(result.broken_links) - 10} more")

    if result.warnings:
        click.echo(f"\n⚠️  {len(result.warnings)} warnings:")
        for warning in result.warnings[:5]:  # Show first 5
            click.echo(f"   • {warning}")
        if len(result.warnings) > 5:
            click.echo(f"   ... and {len(result.warnings) - 5} more")

    if result.errors:
        click.echo(f"\n❌ {len(result.errors)} errors:")
        for error in result.errors:
            click.echo(f"   • {error}")

    click.echo(f"\n⏱️  Validation completed in {result.processing_time:.2f}s")

    if result.success:
        click.echo("✅ Validation passed - vault is ready for conversion")
    else:
        click.echo("❌ Validation failed - please fix errors before conversion")


def _display_conversion_results(result: Any) -> None:
    """Display conversion results to user."""
    click.echo("\n" + "=" * 50)
    click.echo("CONVERSION RESULTS")
    click.echo("=" * 50)

    if result.success:
        click.echo("✅ Conversion completed successfully!")
        click.echo(f"📦 Package created: {result.output_path}")
    else:
        click.echo("❌ Conversion failed!")

    # Statistics
    click.echo("\n📊 Statistics:")
    click.echo(f"   Files processed: {result.files_processed}")
    if hasattr(result, "assets_processed"):
        click.echo(f"   Assets processed: {result.assets_processed}")
    click.echo(f"   Processing time: {result.processing_time:.2f}s")

    # Warnings
    if result.warnings:
        warning_count = len(result.warnings)
        click.echo(f"\n⚠️  {warning_count} warning{'s' if warning_count != 1 else ''}:")
        for warning in result.warnings[:3]:  # Show first 3
            click.echo(f"   • {warning}")
        if len(result.warnings) > 3:
            click.echo(f"   ... and {len(result.warnings) - 3} more")

    # Broken links
    if result.broken_links:
        link_count = len(result.broken_links)
        plural = "s" if link_count != 1 else ""
        click.echo(f"\n🔗 {link_count} broken link{plural} detected:")
        for link in result.broken_links[:3]:  # Show first 3
            click.echo(f"   • {link}")
        if len(result.broken_links) > 3:
            click.echo(f"   ... and {len(result.broken_links) - 3} more")

    # Errors
    if result.errors:
        error_count = len(result.errors)
        click.echo(f"\n❌ {error_count} error{'s' if error_count != 1 else ''}:")
        for error in result.errors:
            click.echo(f"   • {error}")

    # Next steps
    if result.success and result.output_path:
        click.echo("\n🎉 Next steps:")
        click.echo("   1. Open AppFlowy")
        click.echo("   2. Go to Settings → Import")
        click.echo(f"   3. Select the generated package: {result.output_path}")
        click.echo("   4. Follow AppFlowy's import wizard")


# Make convert_command available for testing
__all__ = ["cli", "convert_command", "create_export_use_case"]


if __name__ == "__main__":
    cli()
