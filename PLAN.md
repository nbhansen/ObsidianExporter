# Obsidian to Outline Export - Implementation Plan

## TODO: High Priority Tasks
- [x] Research current codebase structure and understand existing patterns
- [ ] Create OutlinePackage domain model
- [ ] Create ProseMirrorDocument domain model  
- [ ] Implement ProseMirrorDocumentGenerator for markdown conversion
- [ ] Implement OutlineDocumentGenerator
- [ ] Implement OutlinePackageGenerator for ZIP creation
- [ ] Create OutlineExportUseCase
- [ ] Update CLI to support --format outline
- [ ] Write unit tests for new components
- [ ] Write integration tests with real vault data
- [ ] Test generated JSON import in Outline instance

## Codebase Analysis Results

### Current Architecture (Hexagonal/Clean)
The existing codebase follows excellent hexagonal architecture patterns with comprehensive test coverage (81%):

**Domain Layer** (`src/domain/`):
- **Immutable Models**: `VaultStructure`, `TransformedContent`, `VaultIndex`, `ResolvedWikiLink`, `AppFlowyPackage`, `NotionPackage`
- **Domain Services**: `VaultAnalyzer`, `ContentTransformer`, `WikiLinkResolver`, `VaultIndexBuilder`
- **Document Generators**: `AppFlowyDocumentGenerator`, `NotionDocumentGenerator`

**Application Layer** (`src/application/`):
- **Use Cases**: `ExportUseCase`, `NotionExportUseCase` - orchestrate domain services
- **Configuration Objects**: Immutable config and result dataclasses
- **Progress Reporting**: Callback-based progress tracking

**Infrastructure Layer** (`src/infrastructure/`):
- **Adapters**: `FileSystemAdapter` for I/O operations
- **Parsers**: `WikilinkParser`, `CalloutParser`, `BlockReferenceParser` (AST-based, not regex)
- **Package Generators**: `AppFlowyPackageGenerator`, `NotionPackageGenerator` (ZIP creation)
- **LLM Providers**: `GeminiProvider` for optional fuzzy matching

**CLI Layer** (`src/cli.py`):
- Click-based CLI with comprehensive error handling
- Support for multiple formats (`--format appflowy|notion`)
- Validation-only mode and progress reporting

### Current Export Capabilities
1. **AppFlowy Template Format**: Original JSON-based template system
2. **Notion Format**: ZIP packages for AppFlowy's Notion import feature

### Sophisticated Content Processing
- **3-Stage Wikilink Resolution**: Exact path → filename match → LLM fuzzy matching
- **Content Transformation**: Markdown parsing, callout conversion, frontmatter handling
- **Asset Management**: Copy and relink all images/attachments
- **Progress Reporting**: Real-time feedback with callbacks

### Key Patterns to Follow

**Immutable Domain Models** (all frozen dataclasses):
```python
@dataclass(frozen=True)
class VaultStructure:
    path: Path
    markdown_files: List[Path]
    asset_files: List[Path]
    links: Dict[str, List[str]]
    metadata: Dict[str, Dict[str, Any]]
```

**Dependency Injection Pattern**:
```python
class NotionExportUseCase:
    def __init__(
        self,
        vault_analyzer: VaultAnalyzer,
        vault_index_builder: VaultIndexBuilder,
        content_transformer: ContentTransformer,
        notion_document_generator: NotionDocumentGenerator,
        notion_package_generator: NotionPackageGenerator,
        file_system: FileSystemAdapter,
    ):
```

**Use Case Orchestration Pattern**:
```python
def export(self, config: NotionExportConfig) -> NotionExportResult:
    # Stage 1: Analyze vault structure
    # Stage 2: Build vault index 
    # Stage 3: Transform content
    # Stage 4: Generate documents
    # Stage 5: Create package
```

## Outline JSON Import Format Analysis

Based on exploration of `/home/nicolai/dev/outline`, the Outline JSON import expects:

### File Structure:
```
export.zip
├── metadata.json                 # Export metadata
├── Collection Name.json          # One JSON file per collection
└── uploads/                      # Attachments directory
    └── [attachment-files]
```

### Key JSON Structures:

**metadata.json**:
```json
{
  "exportVersion": 1,
  "version": "0.78.0-0", 
  "createdAt": "2024-07-18T18:18:14.221Z",
  "createdById": "user-uuid",
  "createdByEmail": "user@example.com"
}
```

**Collection JSON Structure**:
```json
{
  "collection": {
    "id": "collection-uuid",
    "urlId": "short-id",
    "name": "Collection Name", 
    "data": { /* ProseMirror doc for description */ },
    "documentStructure": [
      {
        "id": "doc-uuid",
        "url": "/doc/doc-title-short-id", 
        "title": "Document Title",
        "children": []
      }
    ]
  },
  "documents": {
    "doc-uuid": {
      "id": "doc-uuid",
      "title": "Document Title",
      "data": { /* ProseMirror document structure */ },
      "createdAt": "2024-07-18T18:03:41.622Z",
      // ... other metadata
    }
  },
  "attachments": {
    "attachment-uuid": {
      "id": "attachment-uuid", 
      "documentId": "doc-uuid",
      "contentType": "image/jpeg",
      "name": "filename.jpg",
      "key": "uploads/path/to/file.jpg"
    }
  }
}
```

**ProseMirror Document Format**:
```json
{
  "type": "doc",
  "content": [
    {
      "type": "paragraph",
      "content": [
        {
          "type": "text", 
          "text": "Some text content"
        }
      ]
    }
  ]
}
```

## Implementation Strategy

### Phase 1: Domain Models
Add to `src/domain/models.py`:
- `OutlinePackage` - Immutable package representation
- `ProseMirrorDocument` - Domain model for ProseMirror format
- `OutlineCollection` - Collection structure with document hierarchy
- `OutlineDocument` - Individual document with metadata
- `OutlineAttachment` - Attachment reference

### Phase 2: Content Conversion  
Create `src/domain/prosemirror_document_generator.py`:
- Convert markdown AST to ProseMirror JSON nodes
- Handle all standard markdown elements (paragraphs, headings, lists, etc.)
- Map Obsidian callouts to appropriate ProseMirror blocks
- Process images and attachment references

### Phase 3: Infrastructure Layer
Create `src/infrastructure/generators/outline_package_generator.py`:
- Generate ZIP with proper structure (metadata.json, collection JSONs, uploads/)
- Handle UUID generation for all entities
- Manage attachment copying and reference updates

### Phase 4: Application Layer
Create `src/application/outline_export_use_case.py`:
- Follow exact same pattern as existing use cases
- Orchestrate vault analysis → content transformation → Outline generation → ZIP creation
- Comprehensive error handling and progress reporting

### Phase 5: CLI Integration
Update `src/cli.py`:
- Add `--format outline` option
- Wire up new use case with dependency injection
- Maintain consistent user experience

## Technical Challenges & Solutions

### 1. Markdown to ProseMirror Conversion
**Challenge**: Convert parsed markdown AST to ProseMirror's node structure
**Solution**: Create systematic mapping for each markdown element type with proper nesting

### 2. Document Hierarchy Management  
**Challenge**: Map Obsidian folder structure to Outline's collection/document hierarchy
**Solution**: Build document structure tree and represent as nested NavigationNode array

### 3. Asset Reference Updates
**Challenge**: Update image/attachment references to use Outline's attachment API format
**Solution**: Track attachments during processing and update references to use `/api/attachments.redirect?id=uuid` format

### 4. UUID Generation & Consistency
**Challenge**: Generate proper UUIDs for all entities and maintain references
**Solution**: Use Python's `uuid4()` and maintain mapping dictionary during processing

## Success Criteria
- [ ] Generate valid Outline JSON import files from Obsidian vaults
- [ ] Successfully import generated files into running Outline instance  
- [ ] Preserve 90%+ of content fidelity including formatting and structure
- [ ] Handle all asset types (images, PDFs, etc.) with proper references
- [ ] Maintain existing code quality standards (81% test coverage, clean architecture)
- [ ] Process typical vault (100-500 notes) reliably through existing pipeline

## Next Steps
1. Start with domain models (`OutlinePackage`, `ProseMirrorDocument`)
2. Implement ProseMirror conversion logic
3. Build package generator following existing patterns
4. Create use case following dependency injection patterns
5. Test with real vault data and Outline import