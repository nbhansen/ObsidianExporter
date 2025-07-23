"""
Wikilink resolver implementing Obsidian's three-stage resolution algorithm.

This domain service resolves wikilinks following Obsidian's precedence:
1. Exact path match
2. Filename match
3. Fuzzy matching (future enhancement)
"""

from pathlib import Path
from typing import Optional

from ..infrastructure.parsers.wikilink_parser import WikiLink
from .fallback_parser import FallbackParser
from .models import ResolvedWikiLink, VaultIndex


class WikiLinkResolver:
    """Domain service for resolving wikilinks using three-stage algorithm."""

    def __init__(self, fallback_parser: Optional[FallbackParser] = None) -> None:
        """
        Initialize WikiLink resolver with optional fallback parser.

        Args:
            fallback_parser: Optional fallback parser for Stage 3 fuzzy matching
        """
        self.fallback_parser = fallback_parser

    def resolve(self, wikilink: WikiLink, vault_index: VaultIndex) -> ResolvedWikiLink:
        """
        Resolve a wikilink using Obsidian's three-stage resolution algorithm.

        Stage 1: Exact path match - [[folder/note]] → check exact path
        Stage 2: Filename match - [[note]] → search by filename stem
        Stage 3: Fuzzy match - Handle variations (future enhancement)

        Args:
            wikilink: The WikiLink to resolve
            vault_index: Index of all vault files for resolution

        Returns:
            ResolvedWikiLink with resolution status and path
        """
        target = wikilink.target.strip()

        # Stage 1: Try exact path match
        resolved_path = self._try_exact_path_match(target, vault_index)
        if resolved_path:
            return ResolvedWikiLink(
                original=wikilink,
                resolved_path=resolved_path,
                is_broken=False,
                target_exists=True,
                resolution_method="exact",
                confidence=1.0,
            )

        # Stage 1.5: Try exact path match with .md extension
        resolved_path = self._try_exact_path_match(f"{target}.md", vault_index)
        if resolved_path:
            return ResolvedWikiLink(
                original=wikilink,
                resolved_path=resolved_path,
                is_broken=False,
                target_exists=True,
                resolution_method="exact",
                confidence=1.0,
            )

        # Stage 2: Try filename match
        resolved_path = self._try_filename_match(target, vault_index)
        if resolved_path:
            return ResolvedWikiLink(
                original=wikilink,
                resolved_path=resolved_path,
                is_broken=False,
                target_exists=True,
                resolution_method="filename",
                confidence=0.9,
            )

        # Stage 3: LLM-assisted fuzzy matching
        if self.fallback_parser:
            vault_files = list(vault_index.all_paths.values())
            fallback_result = self.fallback_parser.resolve_wikilink_fallback(
                wikilink=wikilink,
                vault_files=vault_files,
                current_file=Path("unknown"),  # Could be passed as parameter
            )
            if fallback_result:
                return fallback_result

        # Failed to resolve
        return ResolvedWikiLink(
            original=wikilink,
            resolved_path=None,
            is_broken=True,
            target_exists=False,
            resolution_method="failed",
            confidence=0.0,
        )

    def _try_exact_path_match(
        self, target: str, vault_index: VaultIndex
    ) -> Optional[Path]:
        """
        Try to resolve target as exact path match.

        Args:
            target: Target path to resolve
            vault_index: Vault index for lookup

        Returns:
            Resolved path if found, None otherwise
        """
        # Normalize path separators
        normalized_target = target.replace("\\", "/")

        # Check if exact path exists in vault
        if normalized_target in vault_index.all_paths:
            return vault_index.all_paths[normalized_target]

        return None

    def _try_filename_match(
        self, target: str, vault_index: VaultIndex
    ) -> Optional[Path]:
        """
        Try to resolve target by filename stem match.

        Args:
            target: Target filename stem to resolve
            vault_index: Vault index for lookup

        Returns:
            Resolved path if found, None otherwise
        """
        # Extract filename stem (remove any path components)
        filename_stem = Path(target).name

        # Remove .md extension if present
        if filename_stem.endswith(".md"):
            filename_stem = filename_stem[:-3]

        # Check if filename exists in vault
        if filename_stem in vault_index.files_by_name:
            return vault_index.files_by_name[filename_stem]

        return None
