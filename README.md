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