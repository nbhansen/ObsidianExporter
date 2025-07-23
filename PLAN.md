# Obsidian to AppFlowy Exporter: Development Plan

## 📊 Progress Overview

**Current Phase:** Phase 1 - Foundation & Core Parser ✅ **COMPLETED**  
**Latest Commit:** `7a4d592` - AST-based wikilink extraction with Python-Markdown  
**Test Coverage:** 93.43% (37 tests passing)  
**Architecture:** Hexagonal with dependency injection  
**Code Quality:** ✅ All linting/formatting checks pass  

**Phase 1 Completed:**
1. ✅ Implement file scanning functionality (markdown files discovery)
2. ✅ Add wikilink extraction using AST-based parsing with Python-Markdown
3. ✅ Integrate wikilink extraction with VaultAnalyzer scan_vault method
4. ✅ Real vault testing with actual Obsidian test data

**Ready for Phase 2:** Content Transformation Engine

## Project Overview

Build a Python CLI tool that converts Obsidian vaults to AppFlowy-importable ZIP packages, focusing on content preservation, wikilink conversion, and asset migration.

## Architecture & Key Decisions

### Technology Stack

- **Python 3.8+** with virtual environment (as mandated by CLAUDE.md)
- **Python-Markdown** with custom WikiLink extension for AST-based parsing (avoids regex pitfalls)
- **Click** for CLI interface
- **PyYAML** for frontmatter processing
- **Pathlib/shutil** for file operations
- **Zipfile** for package creation

### Project Structure (following SPEC.md)

```
src/
├── domain/              # Core business logic (hexagonal architecture)
│   ├── models.py       # Data classes (VaultStructure, TransformedContent, etc.)
│   ├── vault_analyzer.py  # Vault analysis logic
│   └── content_transformer.py  # Transformation rules
├── infrastructure/     # External dependencies
│   ├── parsers/        # Obsidian vault parsing
│   ├── generators/     # AppFlowy package creation
│   └── file_system.py  # File operations
├── application/        # Use cases and orchestration
│   └── export_use_case.py
└── cli.py             # Command-line interface
```

## Development Phases (TDD Approach)

### Phase 1: Foundation & Core Parser ✅ **COMPLETED**
**Built:** Hexagonal architecture, vault detection, file scanning, AST-based wikilink extraction with 93.43% test coverage

### Phase 2: Content Transformation Engine (Week 3-4) 🎯 **NEXT**

**Goals:** Wikilink resolution algorithm, callout transformation, YAML frontmatter processing, block reference handling

**Key Features:**
- Three-stage wikilink resolution (exact path → filename → fuzzy matching)
- Callout transformation (`> [!info]` → `> **Info:**` with emoji)
- YAML frontmatter → AppFlowy properties mapping
- Block reference handling (`^block-id` → HTML comments)

### Phase 3: AppFlowy Package Generation (Week 5-6)

**Goals:** AppFlowy JSON document generation, ZIP package assembly, asset bundling

**Key Features:**
- JSON documents with proper node structure (type, children, delta)
- config.json manifest for template import
- Asset bundling with corrected relative paths
- ZIP package compatible with AppFlowy's template import

### Phase 4: CLI & Validation (Week 7-8)

**Goals:** Click-based CLI interface, progress reporting, error handling, performance optimization

**Key Features:**
- Command-line argument parsing and help
- Progress reporting during conversion
- Detailed conversion report (success/failures/warnings)
- Broken link detection and reporting
- Performance optimization for large vaults

## Critical Implementation Details

### Architectural Decision: AST-Based Parsing vs Regex

**Decision:** Use Python-Markdown with custom WikiLinkExtension for AST-based parsing instead of regex patterns.

**Rationale:**
- **Context Awareness**: AST parsing respects markdown structure (code blocks, inline code)
- **Reliability**: Avoids complex regex edge cases and escaping issues  
- **Maintainability**: Easier to extend and debug than regex patterns
- **Standards Compliance**: Leverages proven Python-Markdown infrastructure

**Implementation:**
```python
class WikiLinkInlineProcessor(InlineProcessor):
    """AST-based processor for Obsidian wikilinks."""
    
    def handleMatch(self, m, data):
        # Extract and parse wikilink components
        full_match = m.group(0)
        is_embed = full_match.startswith('!')
        content = full_match[3:-2] if is_embed else full_match[2:-2]
        
        # Parse components: target, alias, header, block_id
        return self._parse_wikilink_content(full_match, content, is_embed)
```

**Benefits Realized:**
- Handles all wikilink variants: `[[Note]]`, `[[Note|Alias]]`, `[[Note#Header]]`, `[[Note^block-id]]`, `![[Embed]]`
- Ignores wikilinks in code blocks and inline code automatically
- 100% test coverage on wikilink extraction with 12 comprehensive tests
- Clean separation of parsing logic from business logic

### Wikilink Resolution Strategy

```python
# Three-stage resolution following Obsidian's precedence
1. Exact path match: [[folder/note]] → check exact path
2. Filename match: [[note]] → search vault for note.md  
3. Fuzzy match: Handle casing/spacing variations
```

### AppFlowy JSON Structure

```python
{
  "document": {
    "type": "page",
    "children": [
      {
        "type": "heading",
        "data": {
          "delta": [{"insert": "Hello AppFlowy!"}],
          "level": 1
        }
      }
    ]
  }
}
```

### Content Transformation Mappings

- `[[Note]]` → `[Note](Note.md)`
- `[[Note|Alias]]` → `[Alias](Note.md)`  
- `> [!info]` → `> **Info:**` with emoji
- `^block-id` → `<!-- block: block-id -->`

## Success Criteria

- 90%+ standard markdown content conversion
- 95%+ wikilink resolution accuracy
- All assets preserved with updated references
- Generate importable AppFlowy ZIP packages
- Process typical vault (100-500 notes) under 2 minutes
- Comprehensive conversion reporting

## Risk Mitigation

- **Wikilink complexity**: Use proven Python-Markdown WikiLinks extension instead of custom markdown-it-py plugin
- **AppFlowy format changes**: Focus on documented template import format
- **Performance**: Use generators for large vault processing
- **Quality**: Strict TDD with 80%+ test coverage as mandated by CLAUDE.md

## Development Standards (per CLAUDE.md)

- All code in virtual environment
- TDD with failing tests first
- Type hints on all functions
- Ruff linting + formatting (zero tolerance)
- Hexagonal architecture with dependency injection
- No global state, immutable objects
- 80%+ test coverage requirement