"""
Wikilink parser for Obsidian markdown content.

This module provides AST-based parsing of Obsidian wikilinks using
Python-Markdown with a custom extension, avoiding the pitfalls of regex.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from xml.etree import ElementTree as etree


@dataclass(frozen=True)
class WikiLink:
    """Immutable representation of a parsed Obsidian wikilink."""
    
    original: str  # Full original text: [[Note|Alias#Header]]
    target: str    # Target note name: Note
    alias: Optional[str] = None      # Display alias: Alias
    header: Optional[str] = None     # Section reference: Header
    block_id: Optional[str] = None   # Block reference: block-id
    is_embed: bool = False           # True for ![[Note]]
    
    
class WikiLinkInlineProcessor(InlineProcessor):
    """
    Markdown inline processor for Obsidian wikilinks.
    
    Handles all wikilink variants:
    - [[Note]] - basic link
    - [[Note|Alias]] - with alias
    - [[Note#Header]] - with header
    - [[Note^block-id]] - with block reference
    - ![[Note]] - embed
    """
    
    def __init__(self, pattern: str, md: markdown.Markdown):
        super().__init__(pattern, md)
        self.md = md
        # Store found wikilinks for extraction
        if not hasattr(md, 'wikilinks'):
            md.wikilinks = []
    
    def handleMatch(self, m, data):
        """Process a matched wikilink pattern."""
        # Extract the full match and wikilink content
        full_match = m.group(0)
        is_embed = full_match.startswith('!')
        
        # Remove ![[...]] or [[...]] wrapper
        if is_embed:
            content = full_match[3:-2]  # Remove ![[...]]
        else:
            content = full_match[2:-2]  # Remove [[...]]
        
        # Parse the wikilink content
        wikilink = self._parse_wikilink_content(full_match, content, is_embed)
        
        # Store for later extraction
        self.md.wikilinks.append(wikilink)
        
        # Create a placeholder element (will be removed in post-processing)
        el = etree.Element('span')
        el.text = full_match
        el.set('class', 'wikilink')
        
        return el, m.start(0), m.end(0)
    
    def _parse_wikilink_content(self, original: str, content: str, is_embed: bool) -> WikiLink:
        """Parse the content inside [[...]] to extract components."""
        target = content
        alias = None
        header = None
        block_id = None
        
        # Handle alias: [[Note|Alias]]
        if '|' in content:
            target, alias = content.split('|', 1)
        
        # Handle block reference: [[Note^block-id]]
        if '^' in target:
            target, block_id = target.rsplit('^', 1)
        
        # Handle header reference: [[Note#Header]]
        if '#' in target:
            target, header = target.split('#', 1)
        
        return WikiLink(
            original=original,
            target=target.strip(),
            alias=alias.strip() if alias else None,
            header=header.strip() if header else None,
            block_id=block_id.strip() if block_id else None,
            is_embed=is_embed,
        )


class WikiLinkExtension(Extension):
    """
    Python-Markdown extension for parsing Obsidian wikilinks.
    
    This extension adds support for all Obsidian wikilink variants
    while maintaining context awareness of the markdown AST.
    """
    
    def extendMarkdown(self, md):
        # Pattern matches both [[...]] and ![[...]]
        # Priority 175 ensures it runs before other inline patterns
        wikilink_pattern = WikiLinkInlineProcessor(r'!?\[\[[^\]]+\]\]', md)
        md.inlinePatterns.register(wikilink_pattern, 'wikilink', 175)


class WikiLinkParser:
    """
    High-level interface for extracting wikilinks from markdown content.
    
    Uses Python-Markdown with custom extension for reliable, context-aware parsing.
    """
    
    def __init__(self):
        self.md = markdown.Markdown(extensions=[WikiLinkExtension()])
    
    def extract_wikilinks(self, content: str) -> List[WikiLink]:
        """
        Extract all wikilinks from markdown content.
        
        Args:
            content: Markdown content to parse
            
        Returns:
            List of WikiLink objects found in the content
        """
        # Reset wikilinks for this parse
        self.md.wikilinks = []
        
        # Parse the markdown (this triggers wikilink extraction)
        self.md.convert(content)
        
        # Return found wikilinks
        return self.md.wikilinks.copy()
    
    def extract_from_file(self, file_path: Path) -> List[WikiLink]:
        """
        Extract wikilinks from a markdown file.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            List of WikiLink objects found in the file
        """
        content = file_path.read_text(encoding='utf-8')
        return self.extract_wikilinks(content)