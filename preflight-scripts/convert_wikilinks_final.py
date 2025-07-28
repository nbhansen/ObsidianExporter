#!/usr/bin/env python3
"""
Convert Obsidian wikilinks to standard markdown links for Outline/Notion compatibility
Final version - properly tested
"""

import os
import re
from pathlib import Path

def get_relative_path(from_file, to_file):
    """Get relative path from one file to another"""
    from_path = Path(from_file).parent
    to_path = Path(to_file)
    
    try:
        rel_path = os.path.relpath(to_path, from_path)
        return rel_path.replace('\\', '/')
    except ValueError:
        return str(to_path).replace('\\', '/')

def find_file_in_vault(vault_path, filename):
    """Find a file in the vault by name (without extension)"""
    # Remove .md extension if present
    if filename.endswith('.md'):
        filename = filename[:-3]
    
    # Search for the file
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if file.endswith('.md'):
                file_without_ext = file[:-3]
                if file_without_ext == filename:
                    return os.path.join(root, file)
    
    # If not found, return with .md extension
    return f"{filename}.md"

def convert_wikilinks_in_content(content, current_file_path, vault_path):
    """Convert all wikilinks in content to standard markdown links"""
    
    def replace_wikilink(match):
        """Replace a single wikilink match"""
        full_match = match.group(0)
        link_content = match.group(1)
        
        # Check if it's an embedded file
        is_embed = full_match.startswith('!')
        
        # Parse the link content - handle heading and alias separately
        # First check for alias
        if '|' in link_content:
            parts = link_content.split('|', 1)
            file_and_heading = parts[0]
            alias = parts[1]
        else:
            file_and_heading = link_content
            alias = None
        
        # Now check for heading in the file part
        if '#' in file_and_heading:
            file_name, heading = file_and_heading.split('#', 1)
            heading_part = f"#{heading}"
        else:
            file_name = file_and_heading
            heading_part = ""
        
        # If no alias was provided, use appropriate default
        if alias is None:
            if heading_part and not is_embed:
                # For regular links with headings, show file#heading as text
                alias = f"{file_name}{heading_part}"
            else:
                alias = file_name
        
        # Find the actual file path
        target_path = find_file_in_vault(vault_path, file_name)
        
        # Get relative path from current file to target
        if os.path.exists(target_path):
            rel_path = get_relative_path(current_file_path, target_path)
        else:
            # If file doesn't exist, use the name as-is with .md extension
            rel_path = f"{file_name}.md" if not file_name.endswith('.md') else file_name
        
        # Handle embedded images/files
        if is_embed:
            # Check if it's an image
            image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']
            if any(file_name.lower().endswith(ext) for ext in image_extensions):
                # For images, use standard markdown image syntax
                return f"![{alias}]({rel_path})"
            else:
                # For non-image embeds (PDFs, other md files), convert to a regular link
                return f"[Embedded: {alias}]({rel_path}{heading_part})"
        else:
            # Regular link
            return f"[{alias}]({rel_path}{heading_part})"
    
    # Pattern to match wikilinks (including embedded ones)
    # Matches: [[link]], [[link|alias]], [[link#heading]], [[link#heading|alias]], ![[embed]]
    wikilink_pattern = r'(!?\[\[([^\]]+)\]\])'
    
    # Replace all wikilinks
    converted_content = re.sub(wikilink_pattern, replace_wikilink, content)
    
    return converted_content

def process_file(file_path, vault_path):
    """Process a single markdown file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Convert wikilinks
        converted_content = convert_wikilinks_in_content(content, file_path, vault_path)
        
        # Only write if content changed
        if content != converted_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(converted_content)
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    vault_path = os.getcwd()
    
    print(f"Obsidian Wikilink Converter - Final Version")
    print(f"Vault path: {vault_path}")
    print("=" * 50)
    
    # Test on the test file first
    test_file = os.path.join(vault_path, "test_conversion.md")
    if os.path.exists(test_file):
        print("Testing conversion on test_conversion.md...")
        if process_file(test_file, vault_path):
            print("Test file converted. Please check the output.")
            
            # Show the result
            with open(test_file, 'r') as f:
                print("\nConverted content preview:")
                print("-" * 30)
                for i, line in enumerate(f):
                    if i < 30:  # Show first 30 lines
                        print(line.rstrip())
                print("-" * 30)
            
            response = input("\nDoes this look correct? (yes/no): ")
            if response.lower() != 'yes':
                print("Conversion cancelled. Please check the script.")
                return
    
    # Count all files
    md_files = []
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if file.endswith('.md') and file not in ['fix_wikilinks.py', 'fix_wikilinks_v2.py', 
                                                       'restore_wikilinks.py', 'convert_wikilinks_final.py',
                                                       'test_conversion.md']:
                md_files.append(os.path.join(root, file))
    
    print(f"\nFound {len(md_files)} markdown files to process")
    
    # Process all files
    converted_count = 0
    for i, file_path in enumerate(md_files):
        if i % 50 == 0:  # Progress indicator every 50 files
            print(f"Progress: {i}/{len(md_files)} files processed...")
        
        if process_file(file_path, vault_path):
            converted_count += 1
    
    print("\n" + "=" * 50)
    print(f"Conversion complete!")
    print(f"Files modified: {converted_count}")

if __name__ == "__main__":
    main()