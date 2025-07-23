"""
File system operations for the Obsidian to AppFlowy exporter.

This infrastructure layer provides file system abstractions
following hexagonal architecture principles.
"""

from pathlib import Path
from typing import Protocol


class FileSystemPort(Protocol):
    """Port interface for file system operations."""

    def directory_exists(self, path: Path) -> bool:
        """Check if a directory exists at the given path."""
        ...

    def file_exists(self, path: Path) -> bool:
        """Check if a file exists at the given path."""
        ...

    def list_files(self, path: Path, pattern: str = "*") -> list[Path]:
        """List files in a directory matching the given pattern."""
        ...


class FileSystemAdapter:
    """Concrete file system adapter using pathlib."""

    def directory_exists(self, path: Path) -> bool:
        """Check if a directory exists at the given path."""
        return path.exists() and path.is_dir()

    def file_exists(self, path: Path) -> bool:
        """Check if a file exists at the given path."""
        return path.exists() and path.is_file()

    def list_files(self, path: Path, pattern: str = "*") -> list[Path]:
        """List files in a directory matching the given pattern."""
        if not self.directory_exists(path):
            return []
        return list(path.glob(pattern))
