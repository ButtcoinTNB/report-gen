#!/usr/bin/env python
"""
Script to find and replace any imports from backend.types to backend.app_types
and from ..types to ..app_types in the codebase.
This resolves circular import issues and avoids conflicts with Python's built-in types module.
"""

import os
import re
from pathlib import Path

def fix_file_imports(file_path):
    """
    Fix imports in a single file, replacing 'backend.types' with 'backend.app_types'
    and '..types' with '..app_types'.
    
    Returns True if file was modified, False otherwise.
    """
    file_path = Path(file_path)
    relative_path = os.path.relpath(file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Patterns to replace
        patterns = [
            (r'from backend\.types\.', r'from backend.app_types.'),
            (r'import backend\.types\.', r'import backend.app_types.'),
            (r'from \.\.types\.', r'from ..app_types.'),
            (r'from \.types\.', r'from .app_types.')
        ]
        
        modified = False
        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                modified = True
                
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed imports in {relative_path}")
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {relative_path}: {e}")
        return False

def scan_directory_and_fix_imports(directory):
    """
    Scan the given directory and its subdirectories for Python files
    and fix imports in each file.
    """
    fixed_files_count = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_file_imports(file_path):
                    fixed_files_count += 1
    
    return fixed_files_count

def main():
    """Main function to run the script."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fixed_count = scan_directory_and_fix_imports(backend_dir)
    
    if fixed_count > 0:
        print(f"\nSuccessfully fixed imports in {fixed_count} files.")
    else:
        print("\nNo files needed fixing.")

if __name__ == "__main__":
    main() 