"""
NotionPackageGenerator for creating ZIP packages compatible with Notion import format.

This infrastructure component creates ZIP files containing markdown documents
and assets following the EXACT Notion export format that AppFlowy web import expects.

CRITICAL: Must generate precise file structure without config.json or documents/
directory - just markdown files directly in ZIP root with exact naming format.
"""

import zipfile
from pathlib import Path
from typing import Set

from ...domain.models import NotionPackage


class NotionPackageGenerator:
    """
    Infrastructure service for generating Notion-compatible ZIP packages.

    Creates ZIP files with exact structure for AppFlowy web import:
    - Markdown files directly in ZIP root with "Page Name [32-hex-id].md" format
    - Assets in same directory as referencing page
    - No config.json (Notion format doesn't use it)
    - warnings.txt if warnings present
    """

    def generate_package(self, package: NotionPackage, output_path: Path) -> Path:
        """
        Generate Notion ZIP package from package data.

        Args:
            package: NotionPackage with documents, assets, and warnings
            output_path: Path where ZIP file should be created

        Returns:
            Path to the created ZIP file
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add markdown documents directly to ZIP (no documents/ directory)
            used_paths: Set[str] = set()

            for doc in package.documents:
                # Use the path from document (handles nested structure)
                doc_path = doc.get("path", doc.get("name", "untitled.md"))

                # Resolve conflicts if same path used multiple times
                unique_path = self._resolve_path_conflict(doc_path, used_paths)

                # Add markdown content directly to ZIP
                content = doc.get("content", "")
                zf.writestr(unique_path, content)
                used_paths.add(unique_path)

            # Add assets in their correct directory structure
            for asset_path in package.assets:
                if asset_path.exists():
                    # Determine where asset should be placed in ZIP
                    asset_zip_path = self._determine_asset_zip_path(
                        asset_path, package.documents
                    )
                    zf.write(asset_path, asset_zip_path)

            # Add warnings if present
            if package.warnings:
                warnings_content = "\n".join(package.warnings)
                zf.writestr("warnings.txt", warnings_content)

        return output_path

    def validate_package(self, package_path: Path) -> bool:
        """
        Validate that generated package has correct Notion structure.

        Args:
            package_path: Path to ZIP package file

        Returns:
            True if package structure is valid for Notion import
        """
        if not zipfile.is_zipfile(package_path):
            return False

        try:
            with zipfile.ZipFile(package_path, "r") as zf:
                files = zf.namelist()

                # Should NOT contain config.json (Notion format doesn't use it)
                if "config.json" in files:
                    return False

                # Should NOT contain documents/ directory structure
                if any(f.startswith("documents/") for f in files):
                    return False

                # Should contain at least some markdown files or be empty
                markdown_files = [f for f in files if f.endswith(".md")]

                # Validate markdown filenames follow Notion format (if any exist)
                for md_file in markdown_files:
                    # Extract just filename (not directory path)
                    filename = md_file.split("/")[-1]

                    # Must match "Page Name [32-hex-id].md" format
                    if not self._validate_notion_filename_format(filename):
                        return False

                return True

        except (zipfile.BadZipFile, UnicodeDecodeError):
            return False

    def _resolve_path_conflict(self, desired_path: str, used_paths: Set[str]) -> str:
        """
        Resolve ZIP path conflicts by modifying paths that already exist.

        Args:
            desired_path: The path we want to use
            used_paths: Set of paths already used in ZIP

        Returns:
            Unique path that doesn't conflict
        """
        if desired_path not in used_paths:
            return desired_path

        # For Notion format, conflicts are unlikely due to unique IDs
        # But handle edge cases by appending counter
        base_path = desired_path
        if desired_path.endswith(".md"):
            base_path = desired_path[:-3]
            extension = ".md"
        else:
            extension = ""

        counter = 1
        while True:
            candidate = f"{base_path}_{counter}{extension}"
            if candidate not in used_paths:
                return candidate
            counter += 1

    def _determine_asset_zip_path(self, asset_path: Path, documents: list) -> str:
        """
        Determine where asset should be placed in ZIP structure.

        Args:
            asset_path: Original asset file path
            documents: List of documents that might reference this asset

        Returns:
            Path within ZIP where asset should be stored
        """
        # Look for document that references this asset
        asset_filename = asset_path.name

        for doc in documents:
            content = doc.get("content", "")

            # Check if this document references the asset
            if asset_filename in content:
                # Extract directory from document path for nested structure
                doc_path = doc.get("path", doc.get("name", ""))

                # If document is in a directory, place asset there
                if "/" in doc_path:
                    directory = "/".join(doc_path.split("/")[:-1])
                    return f"{directory}/{asset_filename}"
                else:
                    # Document is at root, but asset should go in page directory
                    # Extract page name and ID from document name
                    doc_name = doc.get("name", "")
                    if doc_name.endswith(".md"):
                        page_dir = doc_name[:-3]  # Remove .md extension
                        return f"{page_dir}/{asset_filename}"

        # Fallback: place in assets/ directory if no referencing document found
        return f"assets/{asset_filename}"

    def _validate_notion_filename_format(self, filename: str) -> bool:
        """
        Validate that filename follows exact Notion format.

        Args:
            filename: Filename to validate

        Returns:
            True if filename matches "Page Name [32-hex-id].md" format
        """
        if not filename.endswith(".md"):
            return False

        # Extract without .md extension
        name_part = filename[:-3]

        # Must contain 32-character hex ID
        # Pattern: "Page Name 32-hex-id" (space separator, not brackets)
        parts = name_part.split(" ")
        if len(parts) < 2:
            return False

        # Last part should be 32-character hex ID
        potential_id = parts[-1]
        if len(potential_id) != 32:
            return False

        # Must be lowercase hex
        try:
            int(potential_id, 16)
            return potential_id.islower()
        except ValueError:
            return False
