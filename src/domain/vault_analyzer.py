"""
Vault analysis logic for the Obsidian to AppFlowy exporter.

This domain service provides vault detection and analysis functionality
following hexagonal architecture with dependency injection.
"""

from pathlib import Path
from typing import List, Protocol

from .models import FolderStructure, VaultStructure, VaultStructureWithFolders


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

    def scan_vault_with_folders(self, vault_path: Path) -> VaultStructureWithFolders:
        """
        Scan an Obsidian vault and return its structure with folder hierarchy.

        Combines original vault scanning with folder structure analysis.

        Args:
            vault_path: Path to the Obsidian vault to scan

        Returns:
            VaultStructureWithFolders containing files and folder hierarchy

        Raises:
            ValueError: If the path is not a valid Obsidian vault
        """
        if not self.is_valid_vault(vault_path):
            raise ValueError(f"Path {vault_path} is not a valid Obsidian vault")

        # Get original vault structure
        vault_structure = self.scan_vault(vault_path)

        # Analyze folder structure
        folder_analyzer = FolderAnalyzer(file_system=self._file_system)
        root_folder = folder_analyzer.analyze_folder_structure(vault_path)

        # Collect all folders in flat list
        all_folders = []

        def collect_folders(folder: FolderStructure) -> None:
            all_folders.append(folder)
            for child in folder.child_folders:
                collect_folders(child)

        collect_folders(root_folder)

        # Build file to folder mapping
        folder_mapping = {}
        for md_file in vault_structure.markdown_files:
            # Find which folder contains this file
            containing_folder = self._find_containing_folder(md_file, all_folders)
            if containing_folder:
                folder_mapping[md_file] = containing_folder

        return VaultStructureWithFolders(
            path=vault_path,
            root_folder=root_folder,
            all_folders=all_folders,
            markdown_files=vault_structure.markdown_files,
            asset_files=vault_structure.asset_files,
            folder_mapping=folder_mapping,
            links=vault_structure.links,
            metadata=vault_structure.metadata,
        )

    def _find_containing_folder(
        self, file_path: Path, all_folders: List[FolderStructure]
    ) -> FolderStructure:
        """Find which folder contains the given file."""
        file_parent = file_path.parent

        # Find folder with exact path match
        for folder in all_folders:
            if folder.path == file_parent:
                return folder

        # If no exact match, return root folder as fallback
        return all_folders[0] if all_folders else None


class FolderAnalyzer:
    """Domain service for analyzing folder structure in Obsidian vaults."""

    def __init__(self, file_system: FileSystemPort) -> None:
        """Initialize with injected file system dependency."""
        self._file_system = file_system

    def analyze_folder_structure(self, vault_path: Path) -> FolderStructure:
        """
        Analyze the folder structure of an Obsidian vault.

        Args:
            vault_path: Path to the vault to analyze

        Returns:
            FolderStructure representing the complete folder hierarchy
        """
        # Get all files to understand folder structure
        all_files = self._file_system.list_files(vault_path, "**/*.*")

        # Filter out .obsidian directory files
        filtered_files = [
            f for f in all_files if not str(f).startswith(str(vault_path / ".obsidian"))
        ]

        # Build folder hierarchy
        return self._build_folder_hierarchy(vault_path, filtered_files)

    def _build_folder_hierarchy(
        self, vault_path: Path, all_files: List[Path]
    ) -> FolderStructure:
        """Build hierarchical folder structure from file paths."""
        # Collect all unique folder paths
        folder_paths = set()
        folder_paths.add(vault_path)  # Add root

        for file_path in all_files:
            # Add all parent directories
            current = file_path.parent
            while (
                current >= vault_path
            ):  # Include vault_path and all its subdirectories
                folder_paths.add(current)
                if current == vault_path:
                    break
                current = current.parent

        # Sort by path depth for building hierarchy
        sorted_folders = sorted(folder_paths, key=lambda p: len(p.parts))

        # Build folder objects
        folder_objects = {}
        for folder_path in sorted_folders:
            level = len(folder_path.relative_to(vault_path).parts)
            if folder_path == vault_path:
                level = 0

            # Find parent path
            parent_path = None
            if folder_path != vault_path:
                parent_path = folder_path.parent

            # Find markdown files in this specific folder (not subfolders)
            folder_md_files = [
                f
                for f in all_files
                if f.parent == folder_path and f.suffix.lower() == ".md"
            ]

            folder_objects[folder_path] = FolderStructure(
                path=folder_path,
                name=folder_path.name,
                parent_path=parent_path,
                child_folders=[],  # Will be populated below
                markdown_files=folder_md_files,
                level=level,
            )

        # Build parent-child relationships
        # First pass: collect children for each parent
        children_by_parent = {}
        for folder_path, folder_obj in folder_objects.items():
            if folder_obj.parent_path and folder_obj.parent_path in folder_objects:
                parent_path = folder_obj.parent_path
                if parent_path not in children_by_parent:
                    children_by_parent[parent_path] = []
                children_by_parent[parent_path].append(folder_obj)

        # Second pass: build hierarchy from deepest to shallowest
        # Sort folders by depth (deepest first) so children are built before parents
        sorted_by_depth = sorted(folder_objects.items(), key=lambda x: -len(x[0].parts))
        final_folder_objects = {}

        for folder_path, folder_obj in sorted_by_depth:
            # Get children that have already been built
            child_folder_objects = []
            if folder_path in children_by_parent:
                for child_folder in children_by_parent[folder_path]:
                    if child_folder.path in final_folder_objects:
                        child_folder_objects.append(
                            final_folder_objects[child_folder.path]
                        )

            final_folder_objects[folder_path] = FolderStructure(
                path=folder_obj.path,
                name=folder_obj.name,
                parent_path=folder_obj.parent_path,
                child_folders=child_folder_objects,
                markdown_files=folder_obj.markdown_files,
                level=folder_obj.level,
            )

        return final_folder_objects[vault_path]
