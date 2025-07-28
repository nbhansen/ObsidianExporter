```
   ___  _         _     _ _            _____                       _            
  / _ \| |__  ___(_) __| (_) __ _ _ __|  ___|_  ___ __   ___  _ __| |_ ___ _ __ 
 | | | | '_ \/ __| |/ _` | |/ _` | '_ \ |_  \ \/ / '_ \ / _ \| '__| __/ _ \ '__|
 | |_| | |_) \__ \ | (_| | | (_| | | | |  _| >  <| |_) | (_) | |  | ||  __/ |   
  \___/|_.__/|___/_|\__,_|_|\__,_|_| |_|_|  /_/\_\ .__/ \___/|_|   \__\___|_|   
                                                 |_|                          
```

# ObsidianExporter

Converts Obsidian vaults to importable packages for AppFlowy, Notion, and Outline. Preserves markdown content, internal document links, assets, and folder structure.

## Problem

Obsidian uses a different format than other note-taking apps for links, content structure, and organization. Direct import between systems isn't possible without conversion.

## Solution

This tool:
- Scans Obsidian vaults and extracts markdown files, assets, and wikilinks
- Transforms Obsidian-specific syntax (wikilinks, callouts, block references) to target formats
- Generates properly structured documents for each target system
- Creates importable packages (ZIP files) for easy migration

## Installation

```bash
git clone <repository-url>
cd ObsidianExporter
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Export formats
Choose your target application with the `--format` option:

```bash
# AppFlowy (default)
python -m src.cli convert /path/to/vault --format appflowy

# Notion format (works with AppFlowy's Notion import)
python -m src.cli convert /path/to/vault --format notion  

# Outline JSON format
python -m src.cli convert /path/to/vault --format outline
```

### Basic conversion
Convert your vault using the default AppFlowy format:
```bash
python -m src.cli convert /path/to/obsidian/vault
```
Creates `vault-name-appflowy-export.zip` in current directory.

### Custom output location and name
```bash
python -m src.cli convert /path/to/vault --format outline --output my-notes.zip --name "My Notes"
```

### Check for issues before converting
Validate your vault to see broken links and potential problems:
```bash
python -m src.cli convert /path/to/vault --format outline --validate-only
```

### Monitor conversion progress
See detailed progress during conversion:
```bash
python -m src.cli convert /path/to/vault --format outline --verbose
```

### Complete example
```bash
# Check vault health first
python -m src.cli convert ~/Documents/MyVault --format outline --validate-only

# If validation passes, convert with progress
python -m src.cli convert ~/Documents/MyVault --format outline --output ~/Desktop/my-notes.zip --verbose

# Or use nested documents for better hierarchy
python -m src.cli convert ~/Documents/MyVault --format outline --nested-documents --output ~/Desktop/my-notes.zip
```

## What gets converted

- **Markdown files**: Content preserved with syntax transformation
- **Internal links**: `[[Page Name]]` → working document links in target system
- **Link aliases**: `[[Document|Display Text]]` → preserves custom display text
- **Case-insensitive linking**: Links work regardless of case differences
- **Assets**: Images and attachments copied to package
- **Callouts**: Obsidian callouts → equivalent formats where supported
- **Block references**: `^block-id` → target system format
- **Folder structure**: Maintained as collections/folders in target system
- **Frontmatter**: YAML metadata converted to document properties

## What doesn't get converted

- Obsidian plugins and their data
- Canvas files
- Complex embedded content
- Plugin-specific syntax (Dataview, Templater, etc.)

## Import instructions

### AppFlowy
1. Run the converter with `--format appflowy`
2. Open AppFlowy
3. Go to Settings → Import
4. Select the generated ZIP file
5. Follow AppFlowy's import wizard

### Notion (via AppFlowy)
1. Run the converter with `--format notion`
2. Open AppFlowy
3. Go to Settings → Import → Import from Notion
4. Select the generated ZIP file
5. Follow the import process

### Outline
1. Run the converter with `--format outline`
2. Open your Outline instance
3. Go to Settings → Import
4. Choose "JSON Export" as import type
5. Upload the generated ZIP file

#### Nested Documents Mode
For Outline exports, use the `--nested-documents` flag to create a hierarchical structure:

```bash
# Traditional: Each folder becomes a separate collection
python -m src.cli convert /path/to/vault --format outline

# Nested: Single collection with nested document hierarchy
python -m src.cli convert /path/to/vault --format outline --nested-documents
```

**Changes with `--nested-documents`:**
- Single collection instead of multiple collections
- Folders become documents with folder icons
- Uses Outline's `parentDocumentId` for hierarchy
- Preserves wikilinks to folders
- Creates nested structure in sidebar

**When to use:**
- Use `--nested-documents` for vault-wide organization with folder hierarchy
- Use default mode for independent collections per folder

## Preparing your Obsidian vault

For best results, clean up wikilinks before export:

- **Fix broken links**: Use Obsidian's "Broken links" core plugin to identify and fix missing targets
- **Match filenames**: Ensure `[[Link Name]]` matches actual filename `Link Name.md`
- **Check case sensitivity**: `[[SurfaceStreams]]` should match `SurfaceStreams.md`, not `surface-streams.md`
- **Use validation**: Run with `--validate-only` to see potential issues before conversion

Well-maintained vaults typically have <50 broken links. More indicates naming mismatches rather than missing content.

### Preflight Scripts

For **Outline exports specifically**, you may need to convert wikilinks to standard markdown format first. Use the preflight scripts in the `preflight-scripts/` folder:

```bash
# Navigate to your vault directory
cd /path/to/your/obsidian/vault

# Convert wikilinks to standard markdown (TESTED WITH OUTLINE)
python /path/to/ObsidianExporter/preflight-scripts/convert_wikilinks_final.py

# If something goes wrong, restore original wikilinks
python /path/to/ObsidianExporter/preflight-scripts/restore_wikilinks.py
```

**⚠️ Important Notes:**
- These scripts have been **tested specifically with Outline exports**
- Make a backup of your vault before running any conversion scripts
- The converter includes testing functionality - it will show you a preview before making changes
- `convert_wikilinks_final.py` converts `[[wikilinks]]` to `[standard markdown links](file.md)`
- `restore_wikilinks.py` can restore malformed conversions if needed

**When to use preflight scripts:**
- If Outline import doesn't handle wikilinks properly after export
- If you experience linking issues in the imported Outline documents
- Only use if the standard export process doesn't work for your use case

## Requirements

- Python 3.11+
- Valid Obsidian vault (contains `.obsidian` folder)
- Target application (AppFlowy, Notion, or Outline) for import

## Testing

```bash
python -m pytest
```

## Architecture

Uses hexagonal architecture with dependency injection:
- **Domain**: Core business logic (vault analysis, content transformation)
- **Infrastructure**: File system, parsers, package generation
- **Application**: Use cases orchestrating the conversion pipeline
- **CLI**: Command-line interface

## License

MIT