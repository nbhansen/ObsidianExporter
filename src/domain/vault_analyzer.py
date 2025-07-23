"""
Vault analysis logic for the Obsidian to AppFlowy exporter.

This domain service provides vault detection and analysis functionality
following hexagonal architecture with dependency injection.
"""

from pathlib import Path
from typing import Protocol

from .models import VaultStructure


class FileSystemPort(Protocol):
    """Port interface for file system operations."""

    def directory_exists(self, path: Path) -> bool:
        """Check if a directory exists at the given path."""
        ...


class VaultAnalyzer:
    """Domain service for analyzing Obsidian vaults."""

    def __init__(self, file_system: FileSystemPort) -> None:
        """Initialize with injected file system dependency."""
        self._file_system = file_system

    def is_valid_vault(self, vault_path: Path) -> bool:
        """
        Determine if the given path contains a valid Obsidian vault.

        A valid vault is identified by the presence of a .obsidian directory.

        Args:
            vault_path: Path to check for vault validity

        Returns:
            True if the path contains a valid Obsidian vault, False otherwise
        """
        obsidian_dir = vault_path / ".obsidian"
        return self._file_system.directory_exists(obsidian_dir)

    def scan_vault(self, vault_path: Path) -> VaultStructure:
        """
        Scan an Obsidian vault and return its structure.

        Discovers all markdown files, asset files, and builds a complete
        inventory of the vault contents.

        Args:
            vault_path: Path to the Obsidian vault to scan

        Returns:
            VaultStructure containing all discovered files and metadata

        Raises:
            ValueError: If the path is not a valid Obsidian vault
        """
        if not self.is_valid_vault(vault_path):
            raise ValueError(f"Path {vault_path} is not a valid Obsidian vault")

        # Discover markdown files
        all_files = self._file_system.list_files(vault_path, "**/*.md")
        markdown_files = [f for f in all_files if f.suffix.lower() == ".md"]

        # Discover asset files
        all_vault_files = self._file_system.list_files(vault_path, "**/*.*")
        asset_files = [
            f
            for f in all_vault_files
            if f.suffix.lower() not in [".md", ".obsidian"]
            and not str(f).startswith(str(vault_path / ".obsidian"))
        ]

        return VaultStructure(
            path=vault_path,
            markdown_files=markdown_files,
            asset_files=asset_files,
            links={},  # Will be populated in later phase
            metadata={},  # Will be populated in later phase
        )
