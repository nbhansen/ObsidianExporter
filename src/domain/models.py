"""
Domain models for the Obsidian to AppFlowy exporter.

These models represent the core business concepts following
hexagonal architecture principles with immutable data classes.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..infrastructure.parsers.wikilink_parser import WikiLink


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
class VaultIndex:
    """Immutable representation of vault file index for wikilink resolution."""

    vault_path: Path
    files_by_name: Dict[str, Path]  # filename stem -> full path
    all_paths: Dict[str, Path]  # relative path -> full path


@dataclass(frozen=True)
class ResolvedWikiLink:
    """Immutable representation of a resolved wikilink."""

    original: WikiLink
    resolved_path: Optional[Path]
    is_broken: bool
    target_exists: bool
    resolution_method: str  # "exact", "filename", "fuzzy", "failed", "llm_fuzzy_match"
    confidence: float = 1.0  # Confidence level of resolution (0.0 - 1.0)


@dataclass(frozen=True)
class AppFlowyPackage:
    """Immutable representation of AppFlowy package ready for export."""

    documents: List[Dict[str, Any]]
    assets: List[Path]
    config: Dict[str, Any]
    warnings: List[str]
