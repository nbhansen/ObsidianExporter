"""
Test cases for wikilink parser functionality.

Following TDD approach - these tests define the expected behavior
for AST-based wikilink extraction from Obsidian markdown.
"""

from pathlib import Path
import tempfile

from src.infrastructure.parsers.wikilink_parser import WikiLink, WikiLinkParser


class TestWikiLinkParser:
    """Test suite for WikiLinkParser following TDD methodology."""

    def test_extract_basic_wikilink(self):
        """Test extraction of basic wikilink: [[Note]]"""
        parser = WikiLinkParser()
        content = "This is a [[Basic Note]] in the text."
        
        result = parser.extract_wikilinks(content)
        
        assert len(result) == 1
        link = result[0]
        assert link.original == "[[Basic Note]]"
        assert link.target == "Basic Note"
        assert link.alias is None
        assert link.header is None
        assert link.block_id is None
        assert link.is_embed is False

    def test_extract_wikilink_with_alias(self):
        """Test extraction of aliased wikilink: [[Note|Alias]]"""
        parser = WikiLinkParser()
        content = "Check out [[Technical Note|this guide]] for details."
        
        result = parser.extract_wikilinks(content)
        
        assert len(result) == 1
        link = result[0]
        assert link.original == "[[Technical Note|this guide]]"
        assert link.target == "Technical Note"
        assert link.alias == "this guide"
        assert link.header is None
        assert link.block_id is None
        assert link.is_embed is False

    def test_extract_wikilink_with_header(self):
        """Test extraction of header wikilink: [[Note#Header]]"""
        parser = WikiLinkParser()
        content = "See [[Project Notes#Implementation Details]] section."
        
        result = parser.extract_wikilinks(content)
        
        assert len(result) == 1
        link = result[0]
        assert link.original == "[[Project Notes#Implementation Details]]"
        assert link.target == "Project Notes"
        assert link.alias is None
        assert link.header == "Implementation Details"
        assert link.block_id is None
        assert link.is_embed is False

    def test_extract_wikilink_with_block_reference(self):
        """Test extraction of block reference wikilink: [[Note^block-id]]"""
        parser = WikiLinkParser()
        content = "Reference this [[Important Note^conclusion-block]] point."
        
        result = parser.extract_wikilinks(content)
        
        assert len(result) == 1
        link = result[0]
        assert link.original == "[[Important Note^conclusion-block]]"
        assert link.target == "Important Note"
        assert link.alias is None
        assert link.header is None
        assert link.block_id == "conclusion-block"
        assert link.is_embed is False

    def test_extract_embed_wikilink(self):
        """Test extraction of embed wikilink: ![[Note]]"""
        parser = WikiLinkParser()
        content = "Here's the embedded content: ![[Embedded Document]]"
        
        result = parser.extract_wikilinks(content)
        
        assert len(result) == 1
        link = result[0]
        assert link.original == "![[Embedded Document]]"
        assert link.target == "Embedded Document"
        assert link.alias is None
        assert link.header is None
        assert link.block_id is None
        assert link.is_embed is True

    def test_extract_complex_wikilink_with_alias_and_header(self):
        """Test extraction of complex wikilink: [[Note#Header|Alias]]"""
        parser = WikiLinkParser()
        content = "Read about [[Advanced Topics#Performance Optimization|optimization tips]]."
        
        result = parser.extract_wikilinks(content)
        
        assert len(result) == 1
        link = result[0]
        assert link.original == "[[Advanced Topics#Performance Optimization|optimization tips]]"
        assert link.target == "Advanced Topics"
        assert link.alias == "optimization tips"
        assert link.header == "Performance Optimization"
        assert link.block_id is None
        assert link.is_embed is False

    def test_extract_multiple_wikilinks(self):
        """Test extraction of multiple wikilinks in same content."""
        parser = WikiLinkParser()
        content = "This document references [[Note A]] and [[Note B|Note B Alias]]. Also see ![[Embedded Note]] and [[Note C#Section]]."
        
        result = parser.extract_wikilinks(content)
        
        assert len(result) == 4
        
        # Check first link
        assert result[0].target == "Note A"
        assert result[0].alias is None
        assert result[0].is_embed is False
        
        # Check second link
        assert result[1].target == "Note B"
        assert result[1].alias == "Note B Alias"
        assert result[1].is_embed is False
        
        # Check third link (embed)
        assert result[2].target == "Embedded Note"
        assert result[2].is_embed is True
        
        # Check fourth link (with header)
        assert result[3].target == "Note C"
        assert result[3].header == "Section"
        assert result[3].is_embed is False

    def test_extract_wikilinks_ignores_code_blocks(self):
        """Test that wikilinks inside code blocks are ignored."""
        parser = WikiLinkParser()
        content = ("This is a real [[Valid Link]].\n\n"
                  "```markdown\n"
                  "This [[Not A Link]] should be ignored.\n"
                  "```\n\n"
                  "Another real [[Another Valid Link]].")
        
        result = parser.extract_wikilinks(content)
        
        assert len(result) == 2
        assert result[0].target == "Valid Link"
        assert result[1].target == "Another Valid Link"

    def test_extract_wikilinks_ignores_inline_code(self):
        """Test that wikilinks inside inline code are ignored."""
        parser = WikiLinkParser()
        content = "Use `[[Not A Link]]` syntax, but [[Real Link]] works."
        
        result = parser.extract_wikilinks(content)
        
        assert len(result) == 1
        assert result[0].target == "Real Link"

    def test_extract_wikilinks_from_file(self):
        """Test extraction of wikilinks from a file."""
        parser = WikiLinkParser()
        content = "This file contains [[File Link]] and ![[Embedded Content]]."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            result = parser.extract_from_file(temp_path)
            
            assert len(result) == 2
            assert result[0].target == "File Link"
            assert result[0].is_embed is False
            assert result[1].target == "Embedded Content"
            assert result[1].is_embed is True
        finally:
            temp_path.unlink()

    def test_extract_no_wikilinks_returns_empty_list(self):
        """Test that content without wikilinks returns empty list."""
        parser = WikiLinkParser()
        content = "This content has no wikilinks, just regular [markdown](links)."
        
        result = parser.extract_wikilinks(content)
        
        assert result == []

    def test_extract_handles_edge_case_wikilinks(self):
        """Test that parser handles edge cases gracefully."""
        parser = WikiLinkParser()
        content = ("Valid: [[Good Link]]\n"
                  "Edge case: [[Multi\nLine Link]]\n"  
                  "Edge case: [[[Triple Brackets]]]\n"
                  "Valid: [[Another Good Link]]")
        
        result = parser.extract_wikilinks(content)
        
        # Parser should handle edge cases gracefully, even if not ideal
        assert len(result) >= 2  # At least the valid ones
        
        # Check that we get the valid links
        targets = [link.target for link in result]
        assert "Good Link" in targets
        assert "Another Good Link" in targets