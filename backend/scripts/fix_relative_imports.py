#!/usr/bin/env python
"""
Fix relative imports beyond top-level package.

This script addresses the "attempted relative import beyond top-level package" error
by changing problematic relative imports (using '..') to absolute imports.

Usage:
    python backend/scripts/fix_relative_imports.py
"""

import os
import re
from pathlib import Path

# Define the backend directory as the root
BACKEND_DIR = Path(__file__).parent.parent.absolute()

def fix_file_imports(file_path):
    """
    Fix imports in a file by converting relative imports to absolute imports.
    
    Args:
        file_path: Path to the file to process
    
    Returns:
        bool: True if changes were made, False otherwise
    """
    relative_path = os.path.relpath(file_path, BACKEND_DIR)
    print(f"Processing {relative_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Match relative imports that go beyond the top-level package
        # For example: from ..utils.xyz import abc
        original_content = content
        
        # Calculate the module path based on the file's location in the directory structure
        module_parts = os.path.dirname(relative_path).split(os.path.sep)
        
        # Find relative imports pattern: from ..[.module] import
        pattern = r'from \.\.(\.?[a-zA-Z0-9_\.]+)? import'
        
        # Process each match individually
        modified_content = content
        for match in re.finditer(pattern, content):
            rel_import = match.group(0)
            # Get the base path part
            module_path = match.group(1) or ""
            
            # Handle based on the depth of the directory
            if len(module_parts) >= 2:
                # We're in a subdirectory (e.g., 'services', 'api', etc.)
                # Determine what's being imported and change to direct import
                top_level = module_parts[0]  # First directory under backend
                
                if module_path.startswith('.'):
                    # Handle deeper relative paths like '...utils'
                    path_depth = module_path.count('.') + 2  # +2 for the '..' prefix
                    segments = module_parts[:-path_depth] if path_depth <= len(module_parts) else []
                    if segments:
                        absolute_import = f'from {".".join(segments)}{module_path.lstrip(".")} import'
                    else:
                        absolute_import = f'from {module_path.lstrip(".")} import'
                else:
                    # Standard case: '..utils' becomes 'utils'
                    absolute_import = f'from {module_path} import'
                
                modified_content = modified_content.replace(rel_import, absolute_import)
        
        # Only write back if we made changes
        if modified_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"  - Fixed imports in {relative_path}")
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {relative_path}: {e}")
        return False

def scan_directory_and_fix_imports():
    """
    Scan all Python files in the backend directory and fix relative imports.
    
    Returns:
        list: List of files that were modified
    """
    fixed_files = []
    
    for root, _, files in os.walk(BACKEND_DIR):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_file_imports(file_path):
                    relative_path = os.path.relpath(file_path, BACKEND_DIR)
                    fixed_files.append(relative_path)
    
    return fixed_files

def main():
    """
    Main function to run the script.
    """
    print("Starting to fix relative imports that go beyond the top-level package...")
    
    fixed_files = scan_directory_and_fix_imports()
    
    if fixed_files:
        print(f"\nSuccessfully fixed imports in {len(fixed_files)} files:")
        for file in fixed_files:
            print(f"- {file}")
    else:
        print("\nNo files needed fixing.")

if __name__ == "__main__":
    main() 