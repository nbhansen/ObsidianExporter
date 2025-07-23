# Obsidian to AppFlowy Exporter: Development Plan

## Project Overview

Build a Python CLI tool that converts Obsidian vaults to AppFlowy-importable ZIP packages, focusing on content preservation, wikilink conversion, and asset migration.

## Architecture & Key Decisions

### Technology Stack

- **Python 3.8+** with virtual environment (as mandated by CLAUDE.md)
- **Standard Python-Markdown** instead of markdown-it-py (better wikilink support via built-in WikiLinks extension)
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

### Phase 1: Foundation & Core Parser (Week 1-2)

**TDD Implementation:**
1. **Write failing tests** for vault detection and basic file scanning
2. **Implement minimal** VaultIndex class with pathlib-based file discovery
3. **Write failing tests** for wikilink extraction using regex
4. **Implement** basic wikilink pattern matching
5. **Write failing tests** for asset inventory generation
6. **Implement** asset discovery logic

**Deliverables:**
- Vault detection (`.obsidian/` directory validation)
- File inventory system (markdown files, assets)
- Basic wikilink extraction using regex patterns
- Asset reference mapping

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