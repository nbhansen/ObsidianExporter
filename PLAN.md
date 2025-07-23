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

### Phase 1: Foundation & Core Parser (Week 1-2) ✅ **COMPLETED**

**TDD Implementation:**
1. ✅ **Write failing tests** for vault detection and basic file scanning
2. ✅ **Implement minimal** VaultAnalyzer class with dependency injection  
3. ✅ **Write failing tests** for wikilink extraction using AST-based parsing
4. ✅ **Implement** WikiLinkParser with Python-Markdown custom extension
5. ✅ **Write failing tests** for wikilink integration with VaultAnalyzer
6. ✅ **Implement** wikilink extraction integration in scan_vault method

**Deliverables:**
- ✅ Vault detection (`.obsidian/` directory validation) - **COMPLETED**
- ✅ File inventory system (markdown files, assets) - **COMPLETED**
- ✅ AST-based wikilink extraction with Python-Markdown - **COMPLETED**
- ✅ Wikilink integration with VaultAnalyzer - **COMPLETED**
- ✅ Asset reference mapping - **COMPLETED**

**Final Status (Phase 1 Complete):**
- ✅ Hexagonal architecture with port-adapter pattern established
- ✅ VaultAnalyzer with dependency injection for FileSystemPort and WikiLinkParserPort
- ✅ FileSystemAdapter with comprehensive file operations
- ✅ WikiLinkParser using AST-based Python-Markdown extension
- ✅ Complete domain models with immutable dataclasses
- ✅ 93.43% test coverage (37 tests passing)
- ✅ Zero-tolerance linting/formatting compliance (ruff)
- ✅ Real vault testing with actual Obsidian test data
- ✅ Integration tests validating end-to-end workflows

### Phase 2: Content Transformation Engine (Week 3-4)

**TDD Implementation:**
1. **Write failing tests** for Python-Markdown with WikiLinks extension
2. **Implement** markdown parsing with custom wikilink resolver
3. **Write failing tests** for callout transformation mappings
4. **Implement** callout → AppFlowy block conversion
5. **Write failing tests** for YAML frontmatter extraction
6. **Implement** metadata processing with PyYAML

**Key Features:**
- Wikilink resolution algorithm (exact path → filename → fuzzy matching)
- Callout transformation (`> [!info]` → `> **Info:**`)
- YAML frontmatter → AppFlowy properties mapping
- Block reference handling (`^block-id` → HTML comments)

### Phase 3: AppFlowy Package Generation (Week 5-6)

**TDD Implementation:**
1. **Write failing tests** for AppFlowy JSON document structure
2. **Implement** document generator following AppFlowy's schema
3. **Write failing tests** for ZIP package assembly
4. **Implement** template package creation with config.json
5. **Write failing tests** for asset bundling and path rewriting
6. **Implement** complete package generation pipeline

**AppFlowy Integration:**
- Generate JSON documents with proper node structure (type, children, delta)
- Create config.json manifest for template import
- Bundle assets with corrected relative paths
- ZIP package compatible with AppFlowy's template import

### Phase 4: CLI & Validation (Week 7-8)

**TDD Implementation:**
1. **Write failing tests** for Click-based CLI interface
2. **Implement** command-line argument parsing and help
3. **Write failing tests** for conversion reporting
4. **Implement** detailed progress and error reporting
5. **Write failing tests** for edge cases and error handling
6. **Implement** graceful degradation and validation

**Features:**
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