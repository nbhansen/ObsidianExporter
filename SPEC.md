# Obsidian to AppFlowy Import Tool: MVP Technical Specification

## Project overview and objectives

This project addresses a specific migration need: transferring a large Obsidian knowledge base to AppFlowy while preserving content structure, internal links, and metadata relationships.

**The migration challenge:** Obsidian vaults often contain hundreds or thousands of interconnected markdown files with complex internal linking, embedded media, metadata, and custom formatting. Manual migration would be prohibitively time-consuming and error-prone, while the structural differences between platforms make direct file copying impossible.

**Core objectives:**
- **Preserve content integrity**: Maintain all markdown text, formatting, and document structure
- **Convert internal links**: Transform Obsidian's wikilink system (`[[Note]]`) to AppFlowy-compatible references
- **Migrate assets**: Copy and relink all images, PDFs, and other attachments
- **Maintain organization**: Preserve folder structure and file relationships
- **Handle metadata**: Convert YAML frontmatter and tags to AppFlowy properties
- **Provide verification**: Generate reports showing what was converted and any limitations

**Success definition:** A working CLI tool that can process a typical Obsidian vault (100-1000 notes) and generate an importable AppFlowy package with 90%+ content fidelity and functional internal linking.

**Non-goals for MVP:** This tool focuses on one-time migration, not ongoing synchronization. Complex plugin-specific syntax, real-time collaboration features, and GUI interfaces are explicitly out of scope.

This document outlines the technical requirements for building this minimal viable CLI tool, emphasizing sound architecture principles and practical implementation over feature completeness.

## Understanding the source and target systems

### Obsidian's markdown implementation

Obsidian extends CommonMark with several proprietary features that require specific handling during conversion:

**Core extensions:**
- **Wikilinks**: `[[Note Name]]`, `[[Note|Alias]]`, `[[Note#Header]]`, `[[Note^block-id]]`
- **Embeds**: `![[image.jpg]]`, `![[Note]]`, `![[Note#Header]]`
- **Callouts**: `> [!info]`, `> [!warning]`, etc. with 13 predefined types
- **Block references**: `^unique-id` at line endings
- **Tags**: Both inline `#tag` and nested `#project/subproject`
- **Highlighting**: `==highlighted text==`

**File structure:**
- Vault = any folder containing markdown files
- `.obsidian/` directory contains JSON configuration
- Attachments stored in configurable locations
- YAML frontmatter for metadata

### AppFlowy's import capabilities

AppFlowy uses a Flutter frontend with Rust backend, storing documents as JSON with node-based architecture. Current import infrastructure supports Notion workspace imports and template systems.

**Key capabilities:**
- Markdown import via `markdownToDocument()` function
- JSON document structure with type, attributes, children, and Delta text content
- ZIP-based template import for bundled content with assets
- SQLite storage with offline capability

**Limitations:**
- No public REST API
- Limited native wikilink support
- No graph visualization equivalent

## MVP architecture and implementation strategy

### Technology stack

**Core dependencies:**
- **Runtime**: Python 3.8+ for excellent text processing and file handling
- **Markdown parsing**: `python-markdown` with custom WikiLink extension for AST-based parsing
- **YAML processing**: `PyYAML` for frontmatter extraction
- **File operations**: `pathlib` and `shutil` (built-in) for cross-platform compatibility
- **CLI framework**: `click` for argument parsing and user interaction

**Processing pipeline:**
Python's excellent text processing capabilities combined with AST-based parsing make it ideal for reliable markdown transformation:

```python
from pathlib import Path
import markdown
import yaml
from src.infrastructure.parsers.wikilink_parser import WikiLinkParser

def process_obsidian_file(file_path: Path) -> dict:
    content = file_path.read_text(encoding='utf-8')
    
    # Extract frontmatter
    frontmatter, body = extract_yaml_frontmatter(content)
    
    # AST-based wikilink extraction (context-aware)
    parser = WikiLinkParser()
    wikilinks = parser.extract_wikilinks(body)
    
    # Transform content using markdown AST
    md = markdown.Markdown(extensions=['wikilink_extension'])
    transformed = transform_wikilinks(body, wikilinks)
    transformed = transform_callouts(transformed)
    transformed = extract_tags(transformed)
    
    return {
        'metadata': frontmatter,
        'content': transformed,
        'wikilinks': wikilinks,
        'assets': find_asset_references(body)
    }
```

### Architectural Decision: AST-Based Wikilink Parsing

**Problem:** Obsidian wikilinks (`[[Note]]`, `[[Note|Alias]]`, etc.) require reliable extraction from markdown content while respecting context (code blocks should be ignored).

**Solution:** Custom Python-Markdown extension with AST-based inline processor instead of regex patterns.

**Key Benefits:**
- **Context Awareness**: Automatically ignores wikilinks in code blocks and inline code
- **Reliability**: Handles complex nested structures and edge cases consistently  
- **Maintainability**: Clean separation between parsing logic and business logic
- **Extensibility**: Easy to add support for new wikilink variants

**Implementation Approach:**
```python
class WikiLinkExtension(Extension):
    """Python-Markdown extension for parsing Obsidian wikilinks."""
    
    def extendMarkdown(self, md):
        # Register inline processor for wikilink patterns
        wikilink_pattern = WikiLinkInlineProcessor(r'!?\\[\\[[^\\]]+\\]\\]', md)
        md.inlinePatterns.register(wikilink_pattern, 'wikilink', 175)

class WikiLinkInlineProcessor(InlineProcessor):
    """AST-based processor handling all wikilink variants."""
    
    def handleMatch(self, m, data):
        # Parse: [[target#header^block|alias]] or ![[embed]]
        # Returns: WikiLink(target, alias, header, block_id, is_embed)
        return self._parse_wikilink_content(m.group(0))
```

**Supported Variants:**
- `[[Note]]` - Basic wikilink
- `[[Note|Alias]]` - With display alias  
- `[[Note#Header]]` - Section reference
- `[[Note^block-id]]` - Block reference
- `![[Note]]` - Embedded content
- Complex combinations like `[[Note#Header|Alias]]`

### Core conversion steps

**Step 1: Vault Analysis**
- Scan directory for `.obsidian/` to confirm vault
- Build file inventory (`.md`, assets)
- Extract vault configuration from `.obsidian/app.json`
- Create link relationship map

**Step 2: Content Transformation**
- Parse each markdown file to AST
- Extract frontmatter metadata
- Convert wikilinks to standard markdown links
- Transform callouts to closest AppFlowy equivalent
- Process block references and embeds
- Generate intermediate JSON structure

**Step 3: Asset Migration**
- Copy all referenced images/attachments
- Update asset paths for AppFlowy structure
- Maintain relative path relationships
- Generate asset manifest

**Step 4: AppFlowy Package Generation**
- Create AppFlowy-compatible JSON documents
- Bundle documents and assets into ZIP
- Generate `config.json` manifest
- Output importable package

**Step 5: Manual Import**
- User imports generated ZIP via AppFlowy UI
- Tool provides verification report
- Lists any conversion limitations/losses

## Technical implementation details

### Wikilink resolution algorithm

Handle Obsidian's three-stage link resolution using Python's robust path handling:

1. **Exact path match**: `[[folder/note]]` → check exact path
2. **Filename match**: `[[note]]` → search vault for `note.md`
3. **Fuzzy match**: Handle variations in casing/spacing

```python
import re
from pathlib import Path
from typing import Optional, List

class VaultIndex:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.files = {}  # filename -> full_path mapping
        self.paths = set()  # all valid paths
        self._build_index()
    
    def _build_index(self):
        for md_file in self.vault_path.rglob("*.md"):
            rel_path = md_file.relative_to(self.vault_path)
            self.paths.add(str(rel_path))
            self.files[md_file.stem] = str(rel_path)

def resolve_wikilink(link: str, current_path: Path, vault: VaultIndex) -> str:
    """Resolve wikilink following Obsidian's precedence rules."""
    # Remove any heading/block references
    clean_link = re.sub(r'[#^].*$', '', link)
    
    # Try exact path first
    if clean_link in vault.paths:
        return clean_link
    
    # Try filename match
    if clean_link in vault.files:
        return vault.files[clean_link]
    
    # Try with .md extension
    md_link = f"{clean_link}.md"
    if md_link in vault.paths:
        return md_link
    
    # No match found
    print(f"Warning: Broken link '{link}' in {current_path}")
    return f"#broken-link-{clean_link}"
```

### Content transformation mappings

**Wikilinks to markdown links:**
- `[[Note]]` → `[Note](Note.md)`
- `[[Note|Alias]]` → `[Alias](Note.md)`
- `[[Note#Header]]` → `[Note#Header](Note.md#header)`

**Callouts to AppFlowy blocks:**
- `> [!info]` → `> **Info:** ` (quoted block with emphasis)
- `> [!warning]` → `> ⚠️ **Warning:** `
- `> [!note]` → `> 📝 **Note:** `

**Block references:**
- `^block-id` → Convert to HTML comment `<!-- block: block-id -->`
- `[[Note^block-id]]` → `[Note (see block-id)](Note.md)`

**Metadata handling:**
- YAML frontmatter → AppFlowy properties
- `tags: [tag1, tag2]` → AppFlowy tag system
- `aliases: [alias1]` → Note title variations

### File structure and data flow

```
obsidian-to-appflowy/
├── src/
│   ├── parser/           # Obsidian vault parsing
│   │   ├── __init__.py
│   │   ├── vault.py      # VaultIndex and file discovery
│   │   └── markdown.py   # Markdown parsing utilities
│   ├── transformer/      # Content conversion logic
│   │   ├── __init__.py
│   │   ├── wikilinks.py  # Wikilink resolution and conversion
│   │   ├── callouts.py   # Callout transformation
│   │   └── metadata.py   # YAML frontmatter handling
│   ├── generator/        # AppFlowy package creation
│   │   ├── __init__.py
│   │   ├── appflowy.py   # AppFlowy JSON document generation
│   │   └── package.py    # ZIP package assembly
│   ├── cli.py           # Command-line interface
│   └── main.py          # Entry point
├── requirements.txt      # Python dependencies
├── setup.py             # Package configuration
└── output/              # Generated AppFlowy packages
```

**Data flow using Python dataclasses:**
```python
from dataclasses import dataclass
from typing import List, Dict, Any
from pathlib import Path

@dataclass
class VaultStructure:
    files: List[Path]
    links: Dict[str, List[str]]
    metadata: Dict[str, Dict[str, Any]]
    assets: List[Path]

@dataclass 
class TransformedContent:
    markdown: str
    metadata: Dict[str, Any]
    assets: List[Path]
    warnings: List[str]

@dataclass
class AppFlowyPackage:
    documents: List[Dict[str, Any]]
    assets: List[Path] 
    config: Dict[str, Any]
```

1. **VaultParser** → `VaultStructure` (files, links, metadata)
2. **ContentTransformer** → `TransformedContent` (converted markdown, assets)
3. **PackageGenerator** → `appflowy-import.zip` (importable package)

### Error handling and validation

**Graceful degradation:**
- Unknown callout types → generic quoted blocks
- Complex transclusions → simplified links with notes
- Plugin-specific syntax → HTML comments preserving original

**Validation checks:**
- Verify all internal links resolve
- Confirm asset files exist
- Check for circular references
- Validate generated JSON structure

**Reporting:**
- Summary of files processed
- List of broken/ambiguous links
- Conversion warnings and limitations
- Asset migration status

## MVP scope and limitations

### Included features
- Basic markdown conversion (headers, lists, tables, code blocks)
- Wikilink resolution and conversion
- Simple callout transformation
- Asset copying and path rewriting
- YAML frontmatter to properties mapping
- ZIP package generation for manual import

### Excluded from MVP
- Complex plugin syntax (Dataview, Templater)
- Canvas file conversion
- Graph view recreation
- Real-time sync capabilities
- GUI interface
- Advanced template processing

### Known limitations
- No graph visualization in AppFlowy
- Limited callout type mapping
- Block references lose interactive functionality
- Some formatting may require manual adjustment
- Large vaults may need chunked processing

## Development phases

**Phase 1: Core Parser** (Week 1-2)
- Vault detection and file scanning using `pathlib`
- AST-based wikilink parsing with Python-Markdown custom extension
- Wikilink extraction with context awareness (ignores code blocks)
- Asset inventory generation

**Phase 2: Content Transformation** (Week 3-4)
- Wikilink to markdown link conversion
- Callout transformation using string replacement
- YAML frontmatter extraction with `PyYAML`
- Basic error handling and logging

**Phase 3: Package Generation** (Week 5-6)
- AppFlowy JSON document creation
- ZIP package assembly using `zipfile` (built-in)
- Asset bundling and path rewriting
- CLI interface with `click` and reporting

**Phase 4: Testing and Refinement** (Week 7-8)
- Test with various vault structures
- Edge case handling with Python's robust exception system
- Performance optimization using generators for large vaults
- Documentation and usage examples

## Phase 3 Implementation: AppFlowy Package Generation (COMPLETED)

Phase 3 has been successfully implemented with comprehensive AppFlowy package generation capabilities:

### AppFlowy JSON Document Structure

The implemented `AppFlowyDocumentGenerator` creates documents following AppFlowy's JSON format:

```json
{
  "document": {
    "type": "page",
    "children": [
      {
        "type": "heading",
        "data": {
          "level": 1,
          "delta": [{"insert": "Document Title"}]
        }
      },
      {
        "type": "paragraph", 
        "data": {
          "delta": [
            {"insert": "Text with "},
            {"insert": "bold", "attributes": {"bold": true}},
            {"insert": " and "},
            {"insert": "italic", "attributes": {"italic": true}},
            {"insert": " formatting."}
          ]
        }
      }
    ]
  },
  "properties": {
    "title": "Document Title",
    "tags": ["tag1", "tag2"],
    "created": "2024-01-01"
  }
}
```

### Generated ZIP Package Structure

The `AppFlowyPackageGenerator` creates ZIP packages with this structure:

```
appflowy-export.zip
├── config.json          # AppFlowy template manifest
├── documents/
│   ├── note1.json       # AppFlowy JSON documents
│   └── note2.json
├── assets/              # Referenced files (images, PDFs, etc.)
│   ├── image1.png
│   └── document.pdf
└── warnings.txt         # Conversion warnings (if any)
```

### Key Features Implemented

1. **Comprehensive Markdown Support**: 
   - Headings (H1-H6) with proper level mapping
   - Paragraphs with rich text formatting (bold, italic)
   - Code blocks with language detection
   - Bulleted and numbered lists
   - Images with alt text and URL references
   - Tables with row/column structure
   - Empty file preservation (generates empty paragraphs to prevent data loss)

2. **AppFlowy Template Compatibility**:
   - Valid `config.json` manifest with metadata
   - Document type declarations and counts
   - Asset inventory and path management
   - Warning preservation and reporting

3. **Asset Management**:
   - Asset copying with relative path correction
   - Filename conflict resolution
   - Nested directory structure preservation
   - Binary file handling (images, PDFs, etc.)

4. **Quality Assurance**:
   - 28 comprehensive tests covering all functionality
   - Package structure validation
   - Real vault data testing with `/data/_obsidian/`
   - Error handling for malformed input
   - ZIP compression optimization

### Integration Pipeline

The complete pipeline flow:
1. **Content Transformation** → `TransformedContent` (Phase 2 output)
2. **Document Generation** → AppFlowy JSON format via `AppFlowyDocumentGenerator`
3. **Package Assembly** → ZIP creation via `AppFlowyPackageGenerator`
4. **Validation** → Package structure verification
5. **Output** → Importable `.zip` file for AppFlowy

This implementation enables direct import of converted Obsidian vaults into AppFlowy through the template import feature.

## Success criteria

- Successfully convert 90%+ of standard markdown content
- Resolve 95%+ of internal wikilinks correctly
- Preserve all assets with updated references
- Generate importable AppFlowy packages
- Process typical vault (100-500 notes) in under 2 minutes
- Provide clear conversion reports

This MVP focuses on the essential conversion pipeline while maintaining architectural soundness for future enhancements. The CLI-first approach prioritizes functionality over user experience, enabling rapid development and testing.