#!/usr/bin/env python
"""
Script to fix imports in backend Python files to use absolute import paths.
This ensures compatibility between local development and production environments.

Usage:
    python backend/scripts/fix_imports.py

The script will:
1. Scan all Python files in the backend directory
2. Replace relative imports with absolute imports (e.g., 'from utils.logger' -> 'from utils.logger')
3. Update imports that access modules in the same directory to use the backend prefix
"""

import os
import re
import sys
from pathlib import Path

# Define the backend directory
BACKEND_DIR = Path(__file__).parent.parent.absolute()
ROOT_DIR = BACKEND_DIR.parent

# Modules that should have the 'backend.' prefix
MODULES_TO_PREFIX = [
    'api',
    'utils',
    'models',
    'services',
    'db',
    'config',
    'schemas',
    'middleware',
    'ai',
    'tests',
    'docs',
    'scripts',
    'templates',
    'reference_reports'
]

# Regular expression to find imports
IMPORT_PATTERN = re.compile(r'^(from|import)\s+([a-zA-Z0-9_.]+)\s*(import\s+|as\s+|$)', re.MULTILINE)

def fix_imports_in_file(file_path):
    """Fix imports in a single file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Track if any changes were made
    changes_made = False
    
    # Find all imports and fix them
    def replace_import(match):
        nonlocal changes_made
        
        import_type = match.group(1)  # 'from' or 'import'
        module_path = match.group(2)  # The module path
        rest_of_line = match.group(3)  # The rest of the import line
        
        # Skip if it's already an absolute import with backend prefix
        if module_path.startswith('backend.'):
            return match.group(0)
            
        # Skip standard library and third-party modules
        if (
            '.' not in module_path or 
            module_path.split('.')[0] not in MODULES_TO_PREFIX
        ):
            return match.group(0)
            
        # Fix the import with backend prefix
        prefixed_path = f"backend.{module_path}"
        changes_made = True
        return f"{import_type} {prefixed_path} {rest_of_line}"

    updated_content = IMPORT_PATTERN.sub(replace_import, content)
    
    # Only write back if we made changes
    if changes_made:
        with open(file_path, 'w') as f:
            f.write(updated_content)
        return True
        
    return False

def scan_directory_and_fix_imports():
    """Scan all Python files in the backend directory and fix imports."""
    fixed_files = []
    
    for root, _, files in os.walk(BACKEND_DIR):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_imports_in_file(file_path):
                    relative_path = os.path.relpath(file_path, ROOT_DIR)
                    fixed_files.append(relative_path)
    
    return fixed_files

if __name__ == '__main__':
    print(f"Scanning backend directory: {BACKEND_DIR}")
    fixed_files = scan_directory_and_fix_imports()
    
    if fixed_files:
        print(f"Fixed imports in {len(fixed_files)} files:")
        for file in fixed_files:
            print(f" - {file}")
            
        print("\nAll imports have been updated to use absolute paths.")
    else:
        print("No files needed import fixes.") 