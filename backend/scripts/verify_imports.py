#!/usr/bin/env python
"""
Import Verification Script

This script scans the API modules for missing imports and verifies 
that they follow the hybrid import pattern for compatibility with Render.

Usage:
    python -m backend.scripts.verify_imports

Options:
    --fix       Apply suggested fixes to files
    --verbose   Show detailed information about each file
"""

import os
import re
import sys
import ast
import argparse
from pathlib import Path

# Common imports that should be present in API modules
COMMON_IMPORTS = {
    'typing': ['List', 'Dict', 'Any', 'Optional', 'Union'],
    'fastapi': ['APIRouter', 'Depends', 'HTTPException', 'Form', 'File', 'UploadFile'],
    'pydantic': ['BaseModel', 'UUID4'],
    'utils.file_utils': ['secure_filename', 'safe_path_join'],
    'utils.auth': ['get_current_user'],
    'utils.supabase_helper': ['create_supabase_client', 'supabase_client_context'],
    'utils.exceptions': ['ValidationException', 'DatabaseException', 'FileProcessingException'],
    'api.schemas': ['APIResponse'],
    'models': ['User']
}

# Standard libraries that might be used
STD_LIBS = ['os', 'uuid', 'json', 'asyncio', 'datetime', 'shutil', 'mimetypes']

# API directory to scan
API_DIR = Path("backend/api")

# Hybrid import pattern detection
HYBRID_PATTERN = re.compile(r'try:.*?except\s+ImportError:', re.DOTALL)


class ImportVerifier:
    def __init__(self, fix=False, verbose=False):
        self.fix = fix
        self.verbose = verbose
        self.issues_found = 0
        self.files_with_issues = 0
        self.files_checked = 0
        self.files_fixed = 0

    def log(self, message, level=0):
        """Log a message if verbose mode is enabled or if level is 0"""
        if self.verbose or level == 0:
            print(message)

    def scan_directory(self, directory):
        """Scan a directory for Python files"""
        files = list(directory.glob("*.py"))
        self.log(f"Found {len(files)} Python files in {directory}", 1)
        
        for file_path in files:
            # Skip init files and schema files
            if file_path.name == "__init__.py" or file_path.name in ["schemas.py", "openapi_examples.py"]:
                continue
                
            self.scan_file(file_path)
            
        return self.summarize_results()

    def scan_file(self, file_path):
        """Scan a file for missing imports and hybrid pattern"""
        self.files_checked += 1
        file_issues = 0
        
        self.log(f"\nChecking {file_path}...", 1)
        
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Check for hybrid import pattern
        has_hybrid_pattern = bool(HYBRID_PATTERN.search(content))
        
        # Parse the file to extract imports
        try:
            tree = ast.parse(content)
            imports = self.extract_imports(tree)
            
            # Check for missing standard library imports
            used_std_libs = self.find_used_std_libs(content)
            missing_std_libs = [lib for lib in used_std_libs if not self.is_imported(lib, imports)]
            
            # Check for missing common imports
            missing_common_imports = {}
            for module, names in COMMON_IMPORTS.items():
                for name in names:
                    if re.search(r'\b' + re.escape(name) + r'\b', content) and not self.is_name_imported(name, imports):
                        if module not in missing_common_imports:
                            missing_common_imports[module] = []
                        missing_common_imports[module].append(name)
            
            # Report issues
            if not has_hybrid_pattern:
                self.log(f"❌ Missing hybrid import pattern in {file_path}")
                file_issues += 1
                
            if missing_std_libs:
                self.log(f"❌ Missing standard library imports in {file_path}: {', '.join(missing_std_libs)}")
                file_issues += 1
                
            if missing_common_imports:
                self.log(f"❌ Missing common imports in {file_path}:")
                for module, names in missing_common_imports.items():
                    self.log(f"  - From {module}: {', '.join(names)}")
                file_issues += 1
                
            if file_issues > 0:
                self.files_with_issues += 1
                self.issues_found += file_issues
                
                # Apply fixes if requested
                if self.fix:
                    self.apply_fixes(file_path, content, has_hybrid_pattern, missing_std_libs, missing_common_imports)
            else:
                self.log(f"✅ No issues found in {file_path}", 1)
            
        except SyntaxError as e:
            self.log(f"⚠️ Syntax error in {file_path}: {e}")
            self.issues_found += 1
            self.files_with_issues += 1

    def extract_imports(self, tree):
        """Extract all imports from an AST tree"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append((None, name.name, name.asname or name.name))
            elif isinstance(node, ast.ImportFrom):
                module = node.module
                for name in node.names:
                    imports.append((module, name.name, name.asname or name.name))
                    
        return imports

    def find_used_std_libs(self, content):
        """Find standard libraries that might be used in the content"""
        return [lib for lib in STD_LIBS if re.search(r'\b' + lib + r'\.', content)]

    def is_imported(self, module, imports):
        """Check if a module is imported"""
        for import_from, import_name, _ in imports:
            if import_from is None and import_name == module:
                return True
        return False

    def is_name_imported(self, name, imports):
        """Check if a name is imported"""
        for _, import_name, import_as in imports:
            if import_name == name or import_as == name:
                return True
        return False

    def apply_fixes(self, file_path, content, has_hybrid_pattern, missing_std_libs, missing_common_imports):
        """Apply fixes to a file with issues"""
        self.log(f"Applying fixes to {file_path}...")
        
        # Add missing standard library imports
        if missing_std_libs:
            import_block = '\n'.join([f"import {lib}" for lib in missing_std_libs])
            # Find a good place to add these imports
            if re.search(r'import \w+', content):
                # Add after last import statement
                content = re.sub(r'(import .*?\n)', r'\1' + import_block + '\n', content, count=1)
            else:
                # Add at the beginning of the file after docstring
                content = re.sub(r'(""".+?"""\n\n|)', r'\1' + import_block + '\n\n', content, count=1, flags=re.DOTALL)
        
        # Add missing common imports
        if missing_common_imports:
            # Group imports by module
            module_imports = {}
            for module, names in missing_common_imports.items():
                if module not in module_imports:
                    module_imports[module] = []
                module_imports[module].extend(names)
            
            import_block = '\n'.join([f"from {module} import {', '.join(names)}" for module, names in module_imports.items()])
            
            # Find a good place to add these imports
            if re.search(r'from \w+', content):
                # Add after last from import statement
                content = re.sub(r'(from .*?\n)', r'\1' + import_block + '\n', content, count=1)
            elif re.search(r'import \w+', content):
                # Add after last import statement
                content = re.sub(r'(import .*?\n)', r'\1\n' + import_block + '\n', content, count=1)
            else:
                # Add at the beginning of the file after docstring
                content = re.sub(r'(""".+?"""\n\n|)', r'\1' + import_block + '\n\n', content, count=1, flags=re.DOTALL)
        
        # Add hybrid import pattern if missing
        if not has_hybrid_pattern:
            hybrid_template = """
# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    from config import settings
    from utils.logger import get_logger
    from api.schemas import APIResponse
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    from backend.config import settings
    from backend.utils.logger import get_logger
    from backend.api.schemas import APIResponse

"""
            # Find a good place to add the hybrid pattern
            if re.search(r'from \w+|import \w+', content):
                # Add before first import
                content = re.sub(r'(from \w+|import \w+)', hybrid_template + r'\1', content, count=1)
            else:
                # Add at the beginning of the file after docstring
                content = re.sub(r'(""".+?"""\n\n|)', r'\1' + hybrid_template, content, count=1, flags=re.DOTALL)
        
        # Write the updated content back to the file
        with open(file_path, 'w') as f:
            f.write(content)
            
        self.files_fixed += 1
        self.log(f"✅ Applied fixes to {file_path}")

    def summarize_results(self):
        """Summarize the results of the scan"""
        print("\n" + "="*60)
        print(f"Import Verification Summary:")
        print(f"  Files checked:     {self.files_checked}")
        print(f"  Files with issues: {self.files_with_issues}")
        print(f"  Total issues:      {self.issues_found}")
        
        if self.fix:
            print(f"  Files fixed:       {self.files_fixed}")
            
        print("="*60)
        
        return self.issues_found == 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Verify imports in API modules")
    parser.add_argument("--fix", action="store_true", help="Apply suggested fixes")
    parser.add_argument("--verbose", action="store_true", help="Show detailed information")
    
    args = parser.parse_args()
    
    # Ensure we're running from the project root
    if not os.path.exists("backend/api"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(os.path.join(script_dir, "../.."))
        
    if not os.path.exists("backend/api"):
        print("Error: Could not find backend/api directory. Please run this script from the project root.")
        return 1
        
    verifier = ImportVerifier(fix=args.fix, verbose=args.verbose)
    success = verifier.scan_directory(API_DIR)
    
    if success:
        print("All files meet the import requirements!")
        return 0
    else:
        if not args.fix:
            print("\nTo automatically fix these issues, run the script with the --fix flag:")
            print("python -m backend.scripts.verify_imports --fix")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 