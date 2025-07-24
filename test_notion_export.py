#!/usr/bin/env python3
"""
Test script for Notion export functionality using real Obsidian vault.

This script validates our complete Notion export pipeline by processing
the real vault in /data/_obsidian/ and generating a Notion-compatible ZIP.
"""

import tempfile
import zipfile
from pathlib import Path

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


def progress_callback(message: str) -> None:
    """Print progress messages during export."""
    print(f"📊 {message}")


def validate_notion_zip(zip_path: Path) -> None:
    """Validate the generated Notion ZIP structure."""
    print(f"\n🔍 Validating Notion ZIP: {zip_path}")

    if not zipfile.is_zipfile(zip_path):
        print("❌ Not a valid ZIP file!")
        return

    with zipfile.ZipFile(zip_path, "r") as zf:
        files = zf.namelist()

        print(f"📁 ZIP contains {len(files)} files:")

        # Check for markdown files with correct naming
        markdown_files = [f for f in files if f.endswith(".md")]
        print(f"📝 Found {len(markdown_files)} markdown files")

        # Validate first few filenames follow Notion format
        import re

        valid_notion_names = 0
        for md_file in markdown_files[:5]:  # Check first 5
            filename = md_file.split("/")[-1]  # Get just filename, not full path
            # Pattern: "Page Name 32-hex-id.md"
            if re.match(r"^.+ [a-f0-9]{32}\.md$", filename):
                valid_notion_names += 1
                print(f"✅ Valid Notion filename: {filename}")
            else:
                print(f"❌ Invalid Notion filename: {filename}")

        # Check for assets
        asset_files = [
            f for f in files if not f.endswith(".md") and f != "warnings.txt"
        ]
        print(f"🖼️  Found {len(asset_files)} asset files")

        # Check for warnings
        if "warnings.txt" in files:
            warnings_content = zf.read("warnings.txt").decode("utf-8")
            warning_count = (
                len(warnings_content.strip().split("\n"))
                if warnings_content.strip()
                else 0
            )
            print(f"⚠️  Found {warning_count} warnings")

        # Sample content from a markdown file
        if markdown_files:
            sample_file = markdown_files[0]
            content = zf.read(sample_file).decode("utf-8")
            print(f"\n📄 Sample content from {sample_file}:")
            print("=" * 50)
            print(content[:300] + "..." if len(content) > 300 else content)
            print("=" * 50)


def main():
    """Run the complete Notion export test."""
    print("🚀 Testing Notion Export Pipeline with Real Obsidian Vault")
    print("=" * 60)

    # Set up paths
    vault_path = Path("/home/nicolai/dev/ObsidianExporter/data/_obsidian")

    if not vault_path.exists():
        print(f"❌ Vault path does not exist: {vault_path}")
        return

    print(f"📂 Processing vault: {vault_path}")

    # Initialize dependencies (following hexagonal architecture)
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

    # Create use case with dependency injection
    use_case = NotionExportUseCase(
        vault_analyzer=vault_analyzer,
        vault_index_builder=vault_index_builder,
        content_transformer=content_transformer,
        notion_document_generator=notion_document_generator,
        notion_package_generator=notion_package_generator,
        file_system=file_system,
    )

    # Test with temporary output
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "obsidian_notion_export.zip"

        # Configure export
        config = NotionExportConfig(
            vault_path=vault_path,
            output_path=output_path,
            package_name="ObsidianToNotion",
            progress_callback=progress_callback,
        )

        # Execute export
        print(f"\n🔄 Starting export to: {output_path}")
        result = use_case.export(config)

        # Report results
        print("\n📈 Export Results:")
        print(f"✅ Success: {result.success}")
        print(f"📄 Files processed: {result.files_processed}")
        print(f"🖼️  Assets processed: {result.assets_processed}")
        print(f"⏱️  Processing time: {result.processing_time:.2f}s")
        print(f"⚠️  Warnings: {len(result.warnings)}")
        print(f"❌ Errors: {len(result.errors)}")

        # Show first few warnings/errors
        if result.warnings:
            print("\n⚠️  First 3 warnings:")
            for warning in result.warnings[:3]:
                print(f"   • {warning}")

        if result.errors:
            print("\n❌ First 3 errors:")
            for error in result.errors[:3]:
                print(f"   • {error}")

        # Validate the generated ZIP
        if result.output_path and result.output_path.exists():
            validate_notion_zip(result.output_path)

        # Copy ZIP to visible location for inspection
        if result.output_path and result.output_path.exists():
            final_path = Path(
                "/home/nicolai/dev/ObsidianExporter/test_export_result.zip"
            )
            import shutil

            shutil.copy2(result.output_path, final_path)
            print(f"\n💾 ZIP copied to: {final_path}")

        print("\n🎉 Test completed!")


if __name__ == "__main__":
    main()
