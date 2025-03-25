#!/usr/bin/env python3
"""
Script to fix relative imports that go beyond the top-level package.

This script scans Python files and converts problematic relative imports to absolute imports.
It identifies relative imports that use too many dots (..) and modifies them to use absolute paths
relative to the backend directory.

Usage:
    python scripts/fix_relative_imports.py [--check-only] [--verbose] [path...]
    
    --check-only: Only check for problematic imports without making changes
    --verbose: Print detailed information about found imports
    --safelist: Comma-separated list of modules to skip (to avoid breaking circular dependencies)
    path: Optional path(s) to scan. If not provided, scans entire backend directory.

Example:
    python scripts/fix_relative_imports.py
    python scripts/fix_relative_imports.py --check-only
    python scripts/fix_relative_imports.py services/docx_formatter.py
    python scripts/fix_relative_imports.py --safelist=utils.error_handler,api.schemas
"""

import os
import sys
import re
import argparse
from typing import List, Dict, Set, Tuple, Optional

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Regular expression to match import statements
# Group 1: import type (from or import)
# Group 2: the module being imported
# Group 3: the rest of the import statement (as X or import X, Y, Z)
IMPORT_RE = re.compile(r'^(\s*from\s+)([.]+[a-zA-Z0-9_.]+)(\s+import.*)$')

# Set backend directory as the root for absolute imports
ROOT_DIR = backend_dir

def convert_relative_to_absolute_import(file_path: str, rel_import: str, file_dir: str) -> Optional[str]:
    """
    Convert a relative import to an absolute import.
    
    Args:
        file_path: Path to the file containing the import
        rel_import: The relative import string (e.g., ..utils.helper)
        file_dir: Directory of the file
        
    Returns:
        The absolute import path or None if conversion failed
    """
    # Count the number of dots for parent directory reference
    dot_count = 0
    for char in rel_import:
        if char == '.':
            dot_count += 1
        else:
            break
    
    # Extract the module part (without the dots)
    module_part = rel_import[dot_count:]
    
    # Get the path components of the file directory relative to the root
    rel_dir = os.path.relpath(file_dir, ROOT_DIR)
    dir_parts = rel_dir.split(os.sep)
    
    # If we're going beyond the top-level package, it's a problem
    if dot_count > len(dir_parts):
        return None
    
    # Calculate how many directories to go up
    remaining_dirs = dir_parts[:-dot_count] if dot_count > 0 else dir_parts
    
    # Build the absolute import path
    if not remaining_dirs or remaining_dirs == ['.']:
        # We're at the root, so just use the module part
        abs_import = module_part
    else:
        # Combine the remaining directory parts with the module part
        abs_import = '.'.join(remaining_dirs) + ('.' + module_part if module_part else '')
    
    return abs_import

def fix_file_imports(file_path: str, check_only: bool = False, verbose: bool = False, 
                    safelist: Optional[Set[str]] = None) -> Tuple[bool, int]:
    """
    Fix relative imports in a single file.
    
    Args:
        file_path: Path to the file to fix
        check_only: If True, only check for problematic imports without making changes
        verbose: If True, print detailed information about found imports
        safelist: Set of module patterns to skip (to avoid breaking circular dependencies)
        
    Returns:
        Tuple of (whether file was modified, number of imports fixed)
    """
    file_dir = os.path.dirname(file_path)
    file_modified = False
    imports_fixed = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = content.splitlines()
        new_lines = []
        
        for line in lines:
            match = IMPORT_RE.match(line)
            if match:
                import_type, rel_import, rest = match.groups()
                
                # Check if the module is in the safelist
                if safelist:
                    import_parts = rel_import.lstrip('.').split('.')
                    abs_import_base = convert_relative_to_absolute_import(file_path, rel_import, file_dir)
                    
                    if abs_import_base:
                        for safe_module in safelist:
                            # Skip if this import might be part of a circular dependency
                            if safe_module == abs_import_base or abs_import_base.startswith(safe_module + '.'):
                                if verbose:
                                    print(f"Skipping safelisted import in {file_path}: {rel_import} -> {abs_import_base}")
                                new_lines.append(line)
                                break
                        else:
                            # Not in safelist, proceed with conversion
                            abs_import = convert_relative_to_absolute_import(file_path, rel_import, file_dir)
                            if abs_import:
                                imports_fixed += 1
                                new_line = f"{import_type}{abs_import}{rest}"
                                if verbose:
                                    print(f"Fixed import in {file_path}: {line} -> {new_line}")
                                new_lines.append(new_line)
                                file_modified = True
                            else:
                                new_lines.append(line)
                    else:
                        new_lines.append(line)
                else:
                    # No safelist, proceed with all conversions
                    abs_import = convert_relative_to_absolute_import(file_path, rel_import, file_dir)
                    if abs_import:
                        imports_fixed += 1
                        new_line = f"{import_type}{abs_import}{rest}"
                        if verbose:
                            print(f"Fixed import in {file_path}: {line} -> {new_line}")
                        new_lines.append(new_line)
                        file_modified = True
                    else:
                        new_lines.append(line)
            else:
                new_lines.append(line)
        
        if file_modified and not check_only:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
                
        return file_modified, imports_fixed
    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
        return False, 0

def scan_directory_and_fix_imports(start_path: str, check_only: bool = False, 
                                 verbose: bool = False, 
                                 safelist: Optional[Set[str]] = None) -> Tuple[int, int]:
    """
    Scan a directory recursively and fix imports in all Python files.
    
    Args:
        start_path: Directory to scan
        check_only: If True, only check for problematic imports without making changes
        verbose: If True, print detailed information about found imports
        safelist: Set of module patterns to skip (to avoid breaking circular dependencies)
        
    Returns:
        Tuple of (number of files fixed, number of imports fixed)
    """
    files_fixed = 0
    total_imports_fixed = 0
    
    for root, _, files in os.walk(start_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                modified, imports_fixed = fix_file_imports(file_path, check_only, verbose, safelist)
                if modified:
                    files_fixed += 1
                    total_imports_fixed += imports_fixed
    
    return files_fixed, total_imports_fixed

def parse_safelist(safelist_str: str) -> Set[str]:
    """
    Parse a comma-separated string of module names into a set.
    
    Args:
        safelist_str: Comma-separated list of module names
        
    Returns:
        Set of module names to safelist
    """
    if not safelist_str:
        return set()
    return {module.strip() for module in safelist_str.split(',') if module.strip()}

def main() -> int:
    """
    Main function to run the script.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description='Fix relative imports in Python files.')
    parser.add_argument('--check-only', action='store_true', help='Only check for problematic imports without making changes')
    parser.add_argument('--verbose', action='store_true', help='Print detailed information about found imports')
    parser.add_argument('--safelist', type=str, default='', help='Comma-separated list of modules to skip')
    parser.add_argument('paths', nargs='*', help='Paths to scan (default: entire backend directory)')
    
    args = parser.parse_args()
    
    # Default known circular dependencies to safelist
    default_safelist = {
        'utils.error_handler',
        'api.schemas',
        'services.docx_formatter',
        'utils.resource_manager'
    }
    
    # Combine default safelist with user-provided safelist
    user_safelist = parse_safelist(args.safelist)
    safelist = default_safelist.union(user_safelist)
    
    if args.verbose:
        print(f"Using safelist: {', '.join(sorted(safelist))}")
    
    check_only = args.check_only
    verbose = args.verbose
    paths = args.paths or [backend_dir]
    
    total_files_fixed = 0
    total_imports_fixed = 0
    
    for path in paths:
        if os.path.isdir(path):
            files_fixed, imports_fixed = scan_directory_and_fix_imports(path, check_only, verbose, safelist)
        else:
            modified, imports_fixed = fix_file_imports(path, check_only, verbose, safelist)
            files_fixed = 1 if modified else 0
        
        total_files_fixed += files_fixed
        total_imports_fixed += imports_fixed
    
    action = "would be" if check_only else "were"
    print(f"\nSummary: {total_imports_fixed} imports in {total_files_fixed} files {action} fixed.")
    
    if check_only and total_imports_fixed > 0:
        print("Run without --check-only to apply the changes.")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main()) 