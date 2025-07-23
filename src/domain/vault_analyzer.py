"""
Vault analysis logic for the Obsidian to AppFlowy exporter.

This domain service provides vault detection and analysis functionality
following hexagonal architecture with dependency injection.
"""

from pathlib import Path
from typing import List, Protocol

from .models import VaultStructure


class WikiLinkParserPort(Protocol):
    """Port interface for wikilink parsing operations."""

    def extract_from_file(self, file_path: Path) -> List:
        """Extract wikilinks from a markdown file."""
        ...


class FileSystemPort(Protocol):
    """Port interface for file system operations."""

    def directory_exists(self, path: Path) -> bool:
        """Check if a directory exists at the given path."""
        ...

    def list_files(self, path: Path, pattern: str = "*") -> List[Path]:
        """List files in a directory matching the given pattern."""
        ...

    def read_file_content(self, path: Path) -> str:
        """Read the content of a file as a string."""
        ...


class VaultAnalyzer:
    """Domain service for analyzing Obsidian vaults."""

    def __init__(
        self, file_system: FileSystemPort, wikilink_parser: WikiLinkParserPort
    ) -> None:
        """Initialize with injected dependencies."""
        self._file_system = file_system
        self._wikilink_parser = wikilink_parser

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

        # Extract wikilinks from each markdown file
        links = {}
        for md_file in markdown_files:
            file_wikilinks = self._wikilink_parser.extract_from_file(md_file)
            # Extract target from each wikilink and store by filename
            file_targets = [link.target for link in file_wikilinks]
            links[md_file.name] = file_targets

        return VaultStructure(
            path=vault_path,
            markdown_files=markdown_files,
            asset_files=asset_files,
            links=links,
            metadata={},  # Will be populated in later phase
        )
