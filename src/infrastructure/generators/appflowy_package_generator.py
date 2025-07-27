"""
AppFlowy package generator for creating ZIP packages compatible with AppFlowy import.

This infrastructure component creates ZIP files containing AppFlowy documents,
assets, and configuration files following AppFlowy's template import format.
"""

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Set

from ...domain.models import AppFlowyPackage


class AppFlowyPackageGenerator:
    """
    Infrastructure service for generating AppFlowy-compatible ZIP packages.

    Creates ZIP files with proper structure for AppFlowy template import:
    - config.json: Package manifest and metadata
    - documents/: AppFlowy JSON documents
    - assets/: Referenced files (images, PDFs, etc.)
    """

    def generate_package(self, package: AppFlowyPackage, output_path: Path) -> Path:
        """
        Generate AppFlowy ZIP package from package data.

        Args:
            package: AppFlowyPackage with documents, assets, and config
            output_path: Path where ZIP file should be created

        Returns:
            Path to the created ZIP file
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add config.json
            config_data = self._generate_config(package.config, package)
            zf.writestr("config.json", json.dumps(config_data, indent=2))

            # Add documents
            used_names: Set[str] = set()
            for doc in package.documents:
                doc_name = self._resolve_document_name(
                    doc.get("name", "untitled.json"), used_names
                )
                doc_path = self._get_document_path(doc_name)

                # Remove name from document data before storing
                doc_data = {k: v for k, v in doc.items() if k != "name"}
                zf.writestr(doc_path, json.dumps(doc_data, indent=2))
                used_names.add(doc_name)

            # Add assets
            for asset_path in package.assets:
                if asset_path.exists():
                    asset_zip_path = self._get_asset_path(asset_path)
                    zf.write(asset_path, asset_zip_path)

            # Add warnings if present
            if package.warnings:
                warnings_content = "\n".join(package.warnings)
                zf.writestr("warnings.txt", warnings_content)

        return output_path

    def validate_package(self, package_path: Path) -> bool:
        """
        Validate that generated package has correct structure.

        Args:
            package_path: Path to ZIP package file

        Returns:
            True if package structure is valid for AppFlowy import
        """
        if not zipfile.is_zipfile(package_path):
            return False

        try:
            with zipfile.ZipFile(package_path, "r") as zf:
                files = zf.namelist()

                # Must have config.json
                if "config.json" not in files:
                    return False

                # Validate config.json format
                config_data = json.loads(zf.read("config.json"))
                if not isinstance(config_data, dict):
                    return False

                # Validate document files are JSON
                for file in files:
                    if file.startswith("documents/") and file.endswith(".json"):
                        try:
                            json.loads(zf.read(file))
                        except json.JSONDecodeError:
                            return False

                return True

        except (zipfile.BadZipFile, json.JSONDecodeError, KeyError):
            return False

    def _generate_config(
        self, user_config: Dict[str, Any], package: Optional[AppFlowyPackage] = None
    ) -> Dict[str, Any]:
        """
        Generate config.json manifest for AppFlowy template import.

        Args:
            user_config: User-provided configuration
            package: Complete package data for metadata

        Returns:
            Complete configuration dictionary
        """
        config = {
            "template_type": "obsidian_export",
            "format_version": "1.0",
            "created_by": "ObsidianExporter",
            **user_config,
        }

        # Add document metadata if package provided
        if package:
            config["documents"] = [
                {
                    "name": doc.get("name", "untitled.json"),
                    "type": doc.get("document", {}).get("type", "page"),
                }
                for doc in package.documents
            ]

            config["asset_count"] = len(package.assets)

            # Include warnings summary
            if package.warnings:
                config["has_warnings"] = True
                config["warning_count"] = len(package.warnings)

        return config

    def _resolve_document_name(self, name: str, used_names: Set[str]) -> str:
        """
        Resolve document name conflicts by adding suffixes.

        Args:
            name: Desired document name
            used_names: Set of already used names

        Returns:
            Unique document name
        """
        if name not in used_names:
            return name

        base_name = name
        if name.endswith(".json"):
            base_name = name[:-5]
            extension = ".json"
        else:
            extension = ""

        counter = 1
        while True:
            candidate = f"{base_name}_{counter}{extension}"
            if candidate not in used_names:
                return candidate
            counter += 1

    def _get_document_path(self, document_name: str) -> str:
        """
        Get ZIP path for document file.

        Args:
            document_name: Name of document file

        Returns:
            Path within ZIP file
        """
        return f"documents/{document_name}"

    def _get_asset_path(self, asset_path: Path) -> str:
        """
        Get ZIP path for asset file.

        Args:
            asset_path: Original asset file path

        Returns:
            Path within ZIP file preserving relative structure
        """
        # Use just the filename for assets to avoid deep nesting
        return f"assets/{asset_path.name}"

    def _get_compression_type(self, file_extension: str) -> int:
        """
        Get appropriate compression type for file extension.

        Args:
            file_extension: File extension (e.g., '.json', '.png')

        Returns:
            zipfile compression constant
        """
        # Text files benefit from compression
        text_extensions = {".json", ".txt", ".md", ".html", ".css", ".js", ".xml"}

        if file_extension.lower() in text_extensions:
            return zipfile.ZIP_DEFLATED

        # Binary files may already be compressed
        return zipfile.ZIP_DEFLATED  # Use deflate for everything for simplicity
