"""
Domain models for the Obsidian to AppFlowy exporter.

These models represent the core business concepts following
hexagonal architecture principles with immutable data classes.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class VaultStructure:
    """Immutable representation of an Obsidian vault structure."""

    path: Path
    markdown_files: List[Path]
    asset_files: List[Path]
    links: Dict[str, List[str]]
    metadata: Dict[str, Dict[str, Any]]


@dataclass(frozen=True)
class TransformedContent:
    """Immutable representation of transformed markdown content."""

    original_path: Path
    markdown: str
    metadata: Dict[str, Any]
    assets: List[Path]
    warnings: List[str]


@dataclass(frozen=True)
class AppFlowyPackage:
    """Immutable representation of AppFlowy package ready for export."""

    documents: List[Dict[str, Any]]
    assets: List[Path]
    config: Dict[str, Any]
    warnings: List[str]
