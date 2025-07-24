# Obsidian Export Tool: Technical Specification

## Project overview and objectives

This project provides a migration tool for transferring Obsidian knowledge bases to multiple target systems: AppFlowy, Notion (via AppFlowy import), and Outline. The tool preserves content structure, internal links, and metadata relationships across different platform formats.

**The migration challenge:** Obsidian vaults often contain hundreds or thousands of interconnected markdown files with complex internal linking, embedded media, metadata, and custom formatting. Manual migration would be time-consuming and error-prone, while the structural differences between platforms make direct file copying impossible.

**Core objectives:**
- **Multi-platform support**: Export to AppFlowy templates, Notion-compatible format, and Outline JSON
- **Preserve content integrity**: Maintain all markdown text, formatting, and document structure
- **Convert internal links**: Transform Obsidian's wikilink system (`[[Note]]`) to target-compatible references
- **Migrate assets**: Copy and relink all images, PDFs, and other attachments
- **Maintain organization**: Preserve folder structure and file relationships as collections/folders
- **Handle metadata**: Convert YAML frontmatter and tags to target system properties
- **Provide verification**: Generate reports showing what was converted and any limitations

**Success definition:** A CLI tool that can process typical Obsidian vaults (100-1000 notes) and create importable packages for each target system with 90%+ content fidelity and fully functional internal document linking that preserves the knowledge graph structure.

**Non-goals:** This tool focuses on one-time migration, not ongoing synchronization. Complex plugin-specific syntax, real-time collaboration features, and bidirectional sync are explicitly out of scope.

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

### Target system formats

**AppFlowy templates:**
- JSON-based document structure with page hierarchy
- Delta format for rich text content
- Asset handling through base64 encoding or file references
- Template-based import system

**Notion format (for AppFlowy import):**
- Markdown files with specific naming conventions
- Folder structure preservation
- Asset files in nested directories
- Compatible with AppFlowy's Notion import feature

**Outline JSON import:**
- ZIP file containing JSON export format
- Collection-based document organization
- ProseMirror document structure for content
- Separate attachment handling with upload directory

## Architecture and implementation strategy

### Technology stack

**Core dependencies:**
- **Runtime**: Python 3.11+ for cross-platform compatibility
- **CLI Framework**: Click for command-line interface
- **File handling**: Built-in `zipfile` and `pathlib` for cross-platform file operations
- **Markdown parsing**: Custom AST-based parser for wikilinks and Obsidian syntax
- **Content transformation**: Modular parser system for different syntax elements

**Architecture pattern:**
Hexagonal architecture with dependency injection:

```python
# Domain layer - pure business logic
class OutlineDocumentGenerator:
    def generate_outline_package(contents, vault_name) -> OutlinePackage

# Application layer - orchestration
class OutlineExportUseCase:
    def export(config: OutlineExportConfig) -> OutlineExportResult

# Infrastructure layer - external concerns
class OutlinePackageGenerator:
    def generate_package(package: OutlinePackage, output_path: Path) -> Path
```

### Core conversion pipeline

**Step 1: Vault Analysis**
- Scan vault directory structure for `.obsidian/` to confirm validity
- Build file inventory (`.md` files, assets)
- Create wikilink relationship map
- Generate folder structure analysis

**Step 2: Content Transformation**
- Parse each markdown file with frontmatter extraction
- Convert wikilinks using 3-stage resolution (exact path → filename → fuzzy match)
- Transform callouts to target system equivalents
- Process block references and embeds
- Handle asset references and linking

**Step 3: Format-Specific Generation**
- **AppFlowy**: Generate JSON documents with Delta content format
- **Notion**: Create markdown files with proper naming conventions
- **Outline**: Convert to ProseMirror JSON structure with collection organization

**Step 4: Package Creation**
- Create ZIP file with target-specific structure
- Copy and organize assets in proper directories
- Generate metadata files (when required)
- Handle attachment referencing for each format

**Step 5: Validation and Reporting**
- Validate generated package structure
- Report conversion statistics and warnings
- Identify broken links and conversion limitations

## Technical implementation details

### Wikilink resolution algorithm

Handle Obsidian's three-stage link resolution:

1. **Exact path match**: `[[folder/note]]` → check exact path
2. **Filename match**: `[[note]]` → search vault for `note.md`
3. **Fuzzy match**: Handle variations in casing/spacing

```typescript
class VaultIndex {
  private files: Map<string, string> = new Map(); // filename -> full_path
  private paths: Set<string> = new Set(); // all valid paths
  
  constructor(private vaultStructure: any) {
    this.buildIndex();
  }
  
  private buildIndex(): void {
    // Build file mapping from extracted vault structure
  }
  
  resolveWikilink(link: string, currentPath: string): string {
    const cleanLink = link.replace(/[#^].*$/, '');
    
    // Try exact path first
    if (this.paths.has(cleanLink)) {
      return cleanLink;
    }
    
    // Try filename match
    if (this.files.has(cleanLink)) {
      return this.files.get(cleanLink)!;
    }
    
    // Try with .md extension
    const mdLink = `${cleanLink}.md`;
    if (this.paths.has(mdLink)) {
      return mdLink;
    }
    
    // No match found - return broken link placeholder
    console.warn(`Broken link '${link}' in ${currentPath}`);
    return `#broken-link-${cleanLink}`;
  }
}
```

### Content transformation mappings

**Wikilinks transformation by format:**
- **AppFlowy**: `[[Note]]` → Internal page references
- **Notion**: `[[Note]]` → `[Note](./Note.md)`
- **Outline**: `[[Note]]` → ProseMirror link marks with `/doc/urlId` hrefs for working internal links

**Callouts by format:**
- **AppFlowy**: `> [!info]` → Callout blocks with styling
- **Notion**: `> [!info]` → `> **Info:**` (quoted blocks)
- **Outline**: `> [!info]` → Blockquote nodes with emphasis

**Block references:**
- **AppFlowy**: `^block-id` → Block reference system
- **Notion**: `^block-id` → HTML comments `<!-- block: block-id -->`
- **Outline**: `^block-id` → HTML comments in content

**Metadata handling:**
- **AppFlowy**: YAML frontmatter → Page properties
- **Notion**: YAML frontmatter → File-level metadata
- **Outline**: YAML frontmatter → Document properties and fields

### CLI tool architecture

**Project structure:**
```
src/
├── domain/                         # Business logic
│   ├── models.py                   # Immutable data classes
│   ├── vault_analyzer.py           # Vault structure analysis
│   ├── content_transformer.py      # Content conversion
│   ├── outline_document_generator.py # Outline format generation
│   └── prosemirror_document_generator.py # ProseMirror conversion
├── application/                    # Use cases
│   ├── export_use_case.py          # AppFlowy export
│   ├── notion_export_use_case.py   # Notion export
│   └── outline_export_use_case.py  # Outline export
├── infrastructure/                 # External interfaces
│   ├── file_system.py              # File operations
│   ├── parsers/                    # Syntax parsers
│   └── generators/                 # Package generators
└── cli.py                          # Command-line interface
```

**Data flow:**
```python
@dataclass(frozen=True)
class VaultStructure:
    path: Path
    markdown_files: List[Path]
    asset_files: List[Path]
    links: Dict[str, List[str]]
    metadata: Dict[str, Dict[str, Any]]

@dataclass(frozen=True)
class OutlinePackage:
    metadata: Dict[str, Any]           # Export metadata
    collections: List[Dict[str, Any]]  # Collection structures
    documents: Dict[str, Dict[str, Any]] # Document data
    attachments: Dict[str, Dict[str, Any]] # Attachment data
    warnings: List[str]
```

**Export process:**
1. **CLI invocation** → User specifies format and options
2. **Vault analysis** → Scan files, build index, analyze links
3. **Content transformation** → Convert syntax per target format
4. **Package generation** → Create ZIP with proper structure
5. **Validation** → Verify package integrity and report results

### Error handling and validation

**Graceful degradation:**
- Unknown callout types → generic quoted blocks
- Complex transclusions → simplified links with notes
- Plugin-specific syntax → HTML comments preserving original
- Broken wikilinks → placeholder links with warnings

**Validation checks:**
- Verify ZIP contains valid Obsidian vault
- Confirm all internal links can be resolved
- Check asset files exist and are accessible
- Validate markdown parsing results
- Ensure collection/document creation succeeds

**Reporting:**
- Summary of files processed successfully
- List of broken/ambiguous links with locations
- Conversion warnings and limitations
- Asset migration status and any failures
- Performance metrics (processing time, queue status)

## Integration with Outline's import system

### Required components

**Client-side integration:**
- Add Obsidian import option to `app/scenes/Settings/Import.tsx`
- File upload component with ZIP validation
- Progress tracking and status display
- Import history and management

**Server-side integration:**
- Register ObsidianImportsProcessor with queue system
- Add route handlers to `server/routes/api/imports/imports.ts`
- Database migrations for any additional import metadata
- Plugin registration in main application

**API endpoints:**
- `POST /api/imports` - Initiate Obsidian vault import
- `GET /api/imports/:id` - Check import status
- `DELETE /api/imports/:id` - Cancel/cleanup import

### Queue task architecture

```typescript
class ObsidianImportsProcessor extends ImportsProcessor {
  async canProcess(type: string): Promise<boolean> {
    return type === 'obsidian';
  }
  
  async buildTasksInput(input: { file: File }): Promise<any[]> {
    const vault = await this.parseVault(input.file);
    return vault.files.map(file => ({
      type: 'document',
      path: file.path,
      content: file.content,
      metadata: file.metadata
    }));
  }
  
  async scheduleTask(input: any): Promise<void> {
    await this.addJob('obsidian-import-task', input);
  }
}

class ObsidianImportTask extends APIImportTask {
  async process(): Promise<void> {
    const { path, content, metadata } = this.input;
    
    // Process wikilinks and content
    const processedContent = await this.transformContent(content);
    
    // Create document in Outline
    const document = await this.createDocument({
      title: this.extractTitle(path, metadata),
      text: processedContent,
      ...metadata
    });
    
    this.output = { documentId: document.id };
  }
}
```

## Scope and limitations

### Included features
- Basic markdown conversion (headers, lists, tables, code blocks)
- Wikilink resolution and conversion to standard markdown links
- Simple callout transformation to standard markdown
- Asset upload and URL rewriting
- YAML frontmatter to Outline properties mapping
- Folder structure preservation as collection hierarchy
- Queue-based processing for large vaults

### Excluded features
- Complex plugin syntax (Dataview, Templater)
- Canvas file conversion
- Graph view recreation
- Real-time sync capabilities
- Bidirectional synchronization
- Advanced template processing
- Obsidian-specific formatting preservation

### Known limitations
- No graph visualization equivalent in Outline
- Limited callout type mapping to standard markdown
- Block references lose interactive functionality
- Some complex formatting may require manual adjustment
- Large vaults may take considerable processing time
- Wikilink resolution depends on file naming consistency

## Success criteria

- Successfully convert 90%+ of standard markdown content
- Convert wikilinks to functional internal document links that preserve navigation structure
- Preserve all assets with updated Outline URLs
- Maintain folder structure as collection/document hierarchy
- Process typical vault (100-500 notes) reliably through queue system
- Provide comprehensive conversion reports
- Handle ZIP files up to reasonable size limits (100MB+)
- Integrate seamlessly with existing Outline import UI
