# ObsidianExporter

Converts Obsidian vaults to AppFlowy-importable packages. Preserves markdown content, wikilinks, assets, and folder structure.

## Problem

Obsidian and AppFlowy use different formats for notes and linking. Direct import is not possible without conversion.

## Solution

This tool:
- Scans Obsidian vaults and extracts markdown files, assets, and wikilinks
- Transforms Obsidian-specific syntax (wikilinks, callouts, block references) to AppFlowy format
- Generates AppFlowy JSON documents with proper structure
- Creates ZIP packages that AppFlowy can import

## Installation

```bash
git clone <repository-url>
cd ObsidianExporter
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Basic conversion
Convert your vault to AppFlowy format:
```bash
python -m src.cli convert /path/to/obsidian/vault
```
Creates `vault-name-appflowy-export.zip` in current directory.

### Custom output location and name
```bash
python -m src.cli convert /path/to/vault --output my-notes.zip --name "My Notes"
```

### Check for issues before converting
Validate your vault to see broken links and potential problems:
```bash
python -m src.cli convert /path/to/vault --validate-only
```

### Monitor conversion progress
See detailed progress during conversion:
```bash
python -m src.cli convert /path/to/vault --verbose
```

### Complete example
```bash
# Check vault health first
python -m src.cli convert ~/Documents/MyVault --validate-only

# If validation passes, convert with progress
python -m src.cli convert ~/Documents/MyVault --output ~/Desktop/my-notes.zip --verbose
```

## What gets converted

- **Markdown files**: Content preserved with syntax transformation
- **Wikilinks**: `[[Page Name]]` → proper AppFlowy links
- **Assets**: Images and attachments copied to package
- **Callouts**: Obsidian callouts → AppFlowy equivalents
- **Block references**: `^block-id` → AppFlowy format
- **Folder structure**: Maintained in AppFlowy workspace

## What doesn't get converted

- Obsidian plugins and their data
- Canvas files
- Complex embedded content
- Plugin-specific syntax

## Import to AppFlowy

1. Run the converter to create a ZIP package
2. Open AppFlowy
3. Go to Settings → Import
4. Select the generated ZIP file
5. Follow AppFlowy's import wizard

## Requirements

- Python 3.11+
- Valid Obsidian vault (contains `.obsidian` folder)
- AppFlowy installation for import

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