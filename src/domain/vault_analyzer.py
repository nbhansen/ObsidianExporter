"""
Vault analysis logic for the Obsidian to AppFlowy exporter.

This domain service provides vault detection and analysis functionality
following hexagonal architecture with dependency injection.
"""

from pathlib import Path
from typing import Protocol


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
