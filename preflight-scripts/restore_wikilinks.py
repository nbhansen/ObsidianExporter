#!/usr/bin/env python3
"""
Restore malformed wikilinks back to original format
"""

import os
import re

def restore_file(file_path):
    """Restore malformed wikilinks in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern to match the malformed conversions
        # Matches patterns like: [[[text]]]([[text]].md)
        pattern1 = r'\[\[\[([^\]]+)\]\]\]\(\[\[([^\]]+)\]\]\.md\)'
        # Replace with original wikilink format
        content = re.sub(pattern1, r'[[\1]]', content)
        
        # Pattern to match embedded malformed conversions
        # Matches: [Embedded: ![[text]]](![[text]].md)
        pattern2 = r'\[Embedded: !\[\[([^\]]+)\]\]\]\(!\[\[([^\]]+)\]\]\.md\)'
        # Replace with original embedded format
        content = re.sub(pattern2, r'![[\1]]', content)
        
        # Pattern to match aliases that were broken
        # Matches: [alias]]]([[file.md)
        pattern3 = r'\[([^\]]+)\]\]\]\(\[\[([^\]]+)\.md\)'
        # Replace with original format
        content = re.sub(pattern3, r'[[\2|\1]]', content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    vault_path = os.getcwd()
    
    print("Restoring malformed wikilinks...")
    
    # Process all markdown files
    restored_count = 0
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                if restore_file(file_path):
                    restored_count += 1
    
    print(f"Restored {restored_count} files")

if __name__ == "__main__":
    main()