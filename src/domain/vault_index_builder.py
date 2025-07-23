"""
Vault index builder for wikilink resolution.

This domain service builds indices of vault files to enable efficient
wikilink resolution following hexagonal architecture principles.
"""

from pathlib import Path
from typing import Dict, List, Protocol

from .models import VaultIndex


class FileSystemPort(Protocol):
    """Port interface for file system operations."""

    def list_files(self, path: Path, pattern: str = "*") -> List[Path]:
        """List files in a directory matching the given pattern."""
        ...


class VaultIndexBuilder:
    """Domain service for building vault indices for wikilink resolution."""

    def __init__(self, file_system: FileSystemPort) -> None:
        """Initialize with injected file system dependency."""
        self._file_system = file_system

    def build_index(self, vault_path: Path) -> VaultIndex:
        """
        Build a comprehensive index of all markdown files in the vault.

        Creates mappings for efficient wikilink resolution following
        Obsidian's three-stage resolution precedence.

        Args:
            vault_path: Path to the Obsidian vault to index

        Returns:
            VaultIndex containing file mappings for resolution
        """
        # Get all files recursively
        all_files = self._file_system.list_files(vault_path, "**/*.*")

        # Filter to markdown files only
        markdown_files = [f for f in all_files if f.suffix.lower() == ".md"]

        # Build filename mapping (stem -> path)
        files_by_name: Dict[str, Path] = {}
        for md_file in markdown_files:
            filename_stem = md_file.stem
            # For duplicates, prioritize files closer to root (fewer path components)
            if filename_stem not in files_by_name or len(md_file.parts) < len(
                files_by_name[filename_stem].parts
            ):
                files_by_name[filename_stem] = md_file

        # Build relative path mapping (relative_path -> full_path)
        all_paths: Dict[str, Path] = {}
        for md_file in markdown_files:
            try:
                relative_path = md_file.relative_to(vault_path)
                all_paths[str(relative_path)] = md_file
            except ValueError:
                # File is outside vault path, skip
                continue

        return VaultIndex(
            vault_path=vault_path,
            files_by_name=files_by_name,
            all_paths=all_paths,
        )
