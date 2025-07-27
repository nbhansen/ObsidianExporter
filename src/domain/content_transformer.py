"""
Content transformer for processing Obsidian markdown files.

This domain service orchestrates the transformation of raw Obsidian markdown
into AppFlowy-compatible format, handling wikilinks, frontmatter, assets,
and other Obsidian-specific syntax following hexagonal architecture principles.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Protocol

import yaml

from ..infrastructure.parsers.wikilink_parser import WikiLink
from .models import TransformedContent, VaultIndex
from .wikilink_resolver import WikiLinkResolver


class WikiLinkParserPort(Protocol):
    """Port interface for wikilink parsing operations."""

    def extract_wikilinks(self, markdown_content: str) -> List[WikiLink]:
        """Extract all wikilinks from markdown content."""
        ...


class CalloutParserPort(Protocol):
    """Port interface for callout parsing operations."""

    def transform_callouts(self, markdown_content: str) -> str:
        """Transform Obsidian callouts to AppFlowy format."""
        ...


class BlockReferenceParserPort(Protocol):
    """Port interface for block reference parsing operations."""

    def transform_block_references(self, markdown_content: str) -> str:
        """Transform Obsidian block references to AppFlowy format."""
        ...


class ContentTransformer:
    """Domain service for transforming Obsidian markdown content."""

    def __init__(
        self,
        wikilink_parser: WikiLinkParserPort,
        wikilink_resolver: WikiLinkResolver,
        callout_parser: CalloutParserPort,
        block_reference_parser: BlockReferenceParserPort,
    ) -> None:
        """Initialize with injected dependencies."""
        self._wikilink_parser = wikilink_parser
        self._wikilink_resolver = wikilink_resolver
        self._callout_parser = callout_parser
        self._block_reference_parser = block_reference_parser

    def transform_content(
        self,
        original_path: Path,
        markdown_content: str,
        vault_index: VaultIndex,
    ) -> TransformedContent:
        """
        Transform Obsidian markdown content to AppFlowy-compatible format.

        This method orchestrates the complete transformation pipeline:
        1. Extract YAML frontmatter
        2. Parse and resolve wikilinks
        3. Transform wikilinks to AppFlowy format
        4. Transform Obsidian callouts to AppFlowy format
        5. Transform Obsidian block references to AppFlowy format
        6. Identify asset references
        7. Generate warnings for issues

        Args:
            original_path: Path to the original markdown file
            markdown_content: Raw markdown content to transform
            vault_index: Index of vault files for wikilink resolution

        Returns:
            TransformedContent with processed markdown and metadata
        """
        warnings: List[str] = []
        assets: List[Path] = []

        # Step 1: Extract frontmatter
        content_without_frontmatter, metadata = self._extract_frontmatter(
            markdown_content
        )

        # Step 2: Parse wikilinks
        wikilinks = self._wikilink_parser.extract_wikilinks(content_without_frontmatter)

        # Step 3: Resolve and transform wikilinks
        transformed_content = content_without_frontmatter
        for wikilink in wikilinks:
            resolved = self._wikilink_resolver.resolve(wikilink, vault_index)

            if resolved.is_broken:
                warnings.append(
                    f"Broken wikilink '{wikilink.original}' in {original_path.name}: "
                    f"target '{wikilink.target}' not found"
                )
                # Keep original wikilink for broken links
                continue

            # Transform resolved wikilink to AppFlowy format
            transformed_link = self._transform_wikilink_to_appflowy(resolved)
            transformed_content = transformed_content.replace(
                wikilink.original, transformed_link
            )

            # Track assets for embeds
            if wikilink.is_embed and resolved.resolved_path:
                assets.append(resolved.resolved_path)

        # Step 4: Transform Obsidian callouts to AppFlowy format
        transformed_content = self._callout_parser.transform_callouts(
            transformed_content
        )

        # Step 5: Transform Obsidian block references to AppFlowy format
        transformed_content = self._block_reference_parser.transform_block_references(
            transformed_content
        )

        # Step 6: Find additional asset references (standard markdown images)
        additional_assets = self._find_markdown_assets(
            transformed_content, original_path.parent
        )
        assets.extend(additional_assets)

        return TransformedContent(
            original_path=original_path,
            markdown=transformed_content,
            metadata=metadata,
            assets=assets,
            warnings=warnings,
        )

    def _extract_frontmatter(self, markdown_content: str) -> tuple[str, Dict[str, Any]]:
        """
        Extract YAML frontmatter from markdown content.

        Args:
            markdown_content: Raw markdown with potential frontmatter

        Returns:
            Tuple of (content_without_frontmatter, metadata_dict)
        """
        # Check for YAML frontmatter at start of file
        frontmatter_pattern = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
        match = frontmatter_pattern.match(markdown_content)

        if not match:
            return markdown_content, {}

        try:
            # Parse YAML frontmatter
            yaml_content = match.group(1)
            metadata = yaml.safe_load(yaml_content) or {}

            # Remove frontmatter from content
            content_without_frontmatter = markdown_content[match.end() :]

            return content_without_frontmatter, metadata

        except yaml.YAMLError:
            # If YAML parsing fails, treat as regular content
            return markdown_content, {}

    def _transform_wikilink_to_appflowy(self, resolved_wikilink: Any) -> str:
        """
        Transform a resolved wikilink to AppFlowy-compatible format.

        For now, this converts to standard markdown links.
        Future versions might use AppFlowy-specific link format.

        Args:
            resolved_wikilink: ResolvedWikiLink instance

        Returns:
            AppFlowy-compatible link string
        """
        original = resolved_wikilink.original
        resolved_path = resolved_wikilink.resolved_path

        if not resolved_path:
            # Shouldn't happen for non-broken links, but defensive programming
            return str(original.original)

        # Use alias if available, otherwise use target
        display_text = original.alias or original.target

        # For embeds, use embed syntax
        if original.is_embed:
            # For now, convert to standard markdown image
            return f"![{display_text}]({resolved_path.name})"

        # For regular links, use standard markdown link
        link_target = resolved_path.stem  # Remove .md extension

        # Add header anchor if present
        if original.header:
            link_target += f"#{original.header.lower().replace(' ', '-')}"

        # Add block reference if present (AppFlowy might not support this)
        if original.block_id:
            link_target += f"#{original.block_id}"

        return f"[{display_text}]({link_target})"

    def _find_markdown_assets(self, content: str, base_path: Path) -> List[Path]:
        """
        Find standard markdown image and asset references.

        Args:
            content: Markdown content to scan
            base_path: Base directory for resolving relative paths

        Returns:
            List of asset paths found in content
        """
        assets: List[Path] = []

        # Find standard markdown images: ![alt](path)
        image_pattern = re.compile(r"!\[.*?\]\(([^)]+)\)")
        for match in image_pattern.finditer(content):
            asset_path = match.group(1)

            # Convert relative paths to absolute
            if not asset_path.startswith(("http://", "https://", "/")):
                full_path = base_path / asset_path
                if full_path.exists():
                    assets.append(full_path.resolve())

        return assets
