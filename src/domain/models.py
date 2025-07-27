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


@dataclass(frozen=True)
class NotionPackage:
    """Immutable representation of Notion-compatible package ready for export."""

    documents: List[Dict[str, Any]]  # Markdown documents with metadata
    assets: List[Path]
    warnings: List[str]


@dataclass(frozen=True)
class OutlinePackage:
    """Immutable representation of Outline-compatible package ready for export."""

    metadata: Dict[str, Any]  # Export metadata for metadata.json
    collections: List[Dict[str, Any]]  # Collection structures with document hierarchy
    documents: Dict[str, Dict[str, Any]]  # Document data by ID
    attachments: Dict[str, Dict[str, Any]]  # Attachment data by ID
    warnings: List[str]


@dataclass(frozen=True)
class ProseMirrorDocument:
    """Immutable representation of ProseMirror document structure."""

    type: str  # Node type (e.g., "doc", "paragraph", "text")
    content: List[Dict[str, Any]]  # Child nodes
    attrs: Optional[Dict[str, Any]] = None  # Node attributes


@dataclass(frozen=True)
class FolderStructure:
    """Immutable representation of folder hierarchy in an Obsidian vault."""

    path: Path
    name: str
    parent_path: Optional[Path]
    child_folders: List["FolderStructure"]
    markdown_files: List[Path]
    level: int  # depth in hierarchy (0 = root)


@dataclass(frozen=True)
class VaultStructureWithFolders:
    """Immutable representation of an Obsidian vault structure with folder hierarchy."""

    path: Path
    root_folder: FolderStructure
    all_folders: List[FolderStructure]
    markdown_files: List[Path]
    asset_files: List[Path]
    folder_mapping: Dict[Path, FolderStructure]  # file -> folder mapping
    links: Dict[str, List[str]]
    metadata: Dict[str, Dict[str, Any]]
