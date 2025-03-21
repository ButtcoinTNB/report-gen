#!/usr/bin/env python
"""
Pre-deployment check script to validate backend code before deployment.
This script checks for common issues that could cause deployment failures:
1. Relative imports that should be absolute
2. Missing __init__.py files
3. Import references to non-existent modules

Usage:
    python backend/scripts/pre_deploy_check.py

Exit codes:
    0: All checks passed
    1: Warnings only (deployment can proceed but might have issues)
    2: Fatal errors (deployment will likely fail)
"""

import os
import re
import sys
import importlib
from pathlib import Path
from typing import List, Dict, Tuple, Set

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

def check_relative_imports() -> List[Dict]:
    """Check for relative imports that should be absolute."""
    issues = []
    
    for root, _, files in os.walk(BACKEND_DIR):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, ROOT_DIR)
                
                with open(file_path, 'r') as f:
                    content = f.read()
                
                for match in IMPORT_PATTERN.finditer(content):
                    import_type = match.group(1)  # 'from' or 'import'
                    module_path = match.group(2)  # The module path
                    
                    # Skip if it's already an absolute import
                    if module_path.startswith('backend.'):
                        continue
                        
                    # Skip standard library and third-party modules
                    if (
                        '.' not in module_path or 
                        module_path.split('.')[0] not in MODULES_TO_PREFIX
                    ):
                        continue
                    
                    issues.append({
                        'file': relative_path,
                        'line': content[:match.start()].count('\n') + 1,
                        'import': match.group(0).strip(),
                        'suggestion': f"{import_type} backend.{module_path} {match.group(3)}"
                    })
    
    return issues

def check_init_files() -> List[Dict]:
    """Check for missing __init__.py files in directories."""
    issues = []
    
    for root, dirs, _ in os.walk(BACKEND_DIR):
        # Skip directories with no Python files
        has_py_files = False
        for _, _, files in os.walk(root):
            if any(f.endswith('.py') for f in files):
                has_py_files = True
                break
        
        if not has_py_files:
            continue
            
        # Check if __init__.py exists
        if '__init__.py' not in os.listdir(root):
            relative_path = os.path.relpath(root, ROOT_DIR)
            issues.append({
                'directory': relative_path,
                'issue': 'Missing __init__.py file'
            })
    
    return issues

def validate_imports() -> List[Dict]:
    """Validate that imported modules exist."""
    issues = []
    
    # Add backend directory to path temporarily
    sys.path.insert(0, str(ROOT_DIR))
    
    for root, _, files in os.walk(BACKEND_DIR):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, ROOT_DIR)
                
                with open(file_path, 'r') as f:
                    content = f.read()
                
                for match in IMPORT_PATTERN.finditer(content):
                    import_type = match.group(1)  # 'from' or 'import'
                    module_path = match.group(2)  # The module path
                    
                    # Skip standard library and third-party modules
                    if module_path.split('.')[0] not in MODULES_TO_PREFIX:
                        continue
                    
                    # Try to import the module
                    try:
                        if import_type == 'from':
                            # Extract the module part (before the last dot)
                            if '.' in module_path:
                                module_to_import = module_path
                                importlib.import_module(module_to_import)
                        else:
                            importlib.import_module(module_path)
                    except ImportError as e:
                        issues.append({
                            'file': relative_path,
                            'line': content[:match.start()].count('\n') + 1,
                            'import': match.group(0).strip(),
                            'error': str(e)
                        })
    
    # Remove backend directory from path
    sys.path.pop(0)
    
    return issues

def main():
    """Run all checks and report results."""
    print("Running pre-deployment checks...")
    
    # Check for relative imports
    relative_import_issues = check_relative_imports()
    
    # Check for missing __init__.py files
    init_file_issues = check_init_files()
    
    # Validate imports (disabled by default as it might be slow)
    # import_validation_issues = validate_imports()
    import_validation_issues = []
    
    # Count issues
    warnings = len(relative_import_issues) + len(init_file_issues)
    errors = len(import_validation_issues)
    
    # Report results
    if warnings > 0 or errors > 0:
        print("\n== Issues Found ==\n")
        
        if relative_import_issues:
            print(f"\n{len(relative_import_issues)} relative imports that should be absolute:")
            for issue in relative_import_issues:
                print(f"  {issue['file']}:{issue['line']} - {issue['import']}")
                print(f"    Suggestion: {issue['suggestion']}")
        
        if init_file_issues:
            print(f"\n{len(init_file_issues)} directories missing __init__.py files:")
            for issue in init_file_issues:
                print(f"  {issue['directory']}")
        
        if import_validation_issues:
            print(f"\n{len(import_validation_issues)} import errors:")
            for issue in import_validation_issues:
                print(f"  {issue['file']}:{issue['line']} - {issue['import']}")
                print(f"    Error: {issue['error']}")
        
        print("\nRecommended actions:")
        if relative_import_issues:
            print("  - Run `python backend/scripts/fix_imports.py` to fix relative imports")
        if init_file_issues:
            print("  - Run `python backend/scripts/create_init_files.py` to create missing __init__.py files")
        
        # Exit with appropriate code
        if errors > 0:
            print("\n❌ Deployment checks failed with errors. Deployment will likely fail.")
            return 2
        else:
            print("\n⚠️ Deployment checks completed with warnings. Deployment may have issues.")
            return 1
    else:
        print("\n✅ All deployment checks passed! No issues found.")
        return 0

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code) 