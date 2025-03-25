#!/usr/bin/env python
"""
Import Standardization Script

This script analyzes and standardizes import patterns across all API modules,
implementing the hybrid try/except pattern to ensure compatibility with both
development and production environments.

Usage:
    python -m backend.scripts.standardize_imports

Options:
    --dry-run      Show what would be changed without making modifications
    --verbose      Show detailed information
    --module=NAME  Process only the specified module
"""

import argparse
import glob
import os
import re
import sys

# Template for hybrid import section
HYBRID_IMPORT_TEMPLATE = """
# Use imports with fallbacks for better compatibility across environments
try:
    # First try imports without 'backend.' prefix (for Render)
    {imports}
except ImportError:
    # Fallback to imports with 'backend.' prefix (for local dev)
    {backend_imports}
"""

# Common modules to include in the hybrid pattern
COMMON_HYBRID_MODULES = [
    ("config", "settings"),
    ("utils.logger", "get_logger"),
    ("utils.file_utils", "secure_filename", "safe_path_join"),
    ("utils.auth", "get_current_user"),
    ("utils.supabase_helper", "create_supabase_client", "supabase_client_context"),
    (
        "utils.exceptions",
        "ValidationException",
        "DatabaseException",
        "FileProcessingException",
    ),
    ("api.schemas", "APIResponse"),
    ("models", "User", "Report", "Template"),
]

# Standard library imports to ensure are present
STANDARD_IMPORTS = [
    "import os",
    "import uuid",
    "import json",
    "from datetime import datetime",
    "from typing import List, Dict, Any, Optional, Union",
]

# FastAPI imports to ensure are present
FASTAPI_IMPORTS = [
    "from fastapi import APIRouter, Depends, HTTPException",
    "from fastapi.responses import JSONResponse",
    "from pydantic import BaseModel, UUID4",
]


class ImportStandardizer:
    def __init__(self, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.files_processed = 0
        self.files_modified = 0
        self.action_prefix = "[DRY RUN] " if dry_run else ""

    def log(self, message, level=0):
        """Log a message at the specified level"""
        if self.verbose or level == 0:
            print(message)

    def process_directory(self, directory):
        """Process all Python files in the directory"""
        self.log(f"{self.action_prefix}Processing directory: {directory}", 1)

        # Get all Python files in the directory (excluding __init__.py and schemas.py)
        python_files = [
            f
            for f in glob.glob(os.path.join(directory, "*.py"))
            if os.path.basename(f)
            not in ["__init__.py", "schemas.py", "openapi_examples.py"]
        ]

        self.log(f"Found {len(python_files)} Python files to process", 1)

        for file_path in python_files:
            self.process_file(file_path)

        self.print_summary()

    def process_file(self, file_path):
        """Process a single Python file"""
        file_name = os.path.basename(file_path)
        self.log(f"{self.action_prefix}Processing: {file_name}", 0)

        with open(file_path, "r") as f:
            content = f.read()

        # Check if the file already has the hybrid import pattern
        if re.search(r"try:.*?except\s+ImportError:", content, re.DOTALL):
            self.log("  ✓ Already has hybrid import pattern", 1)
            return

        modified_content = self.standardize_imports(content, file_path)

        # Only count as modified if there are actual changes
        if modified_content != content:
            self.files_modified += 1

            if not self.dry_run:
                with open(file_path, "w") as f:
                    f.write(modified_content)
                self.log(f"  ✓ Applied standardized imports to {file_name}", 0)
            else:
                self.log(f"  ✓ Would apply standardized imports to {file_name}", 0)
        else:
            self.log(f"  ✓ No changes needed for {file_name}", 1)

        self.files_processed += 1

    def standardize_imports(self, content, file_path):
        """Standardize imports in the file content"""
        # Extract specific backend imports from the file
        backend_imports = self.extract_backend_imports(content)

        # Add common imports that should be included in most API modules
        imports_to_add = self.identify_additional_imports(content, file_path)

        # Generate the hybrid import section
        hybrid_imports = []
        hybrid_backend_imports = []

        # Add extracted backend imports to hybrid section
        for import_from, import_what in backend_imports:
            # Convert from backend.x.y to x.y for the try block
            if import_from.startswith("backend."):
                non_backend_path = import_from[8:]  # Remove 'backend.'
                hybrid_imports.append(f"from {non_backend_path} import {import_what}")
                hybrid_backend_imports.append(
                    f"from {import_from} import {import_what}"
                )

        # Add common hybrid imports
        for module_parts in COMMON_HYBRID_MODULES:
            module = module_parts[0]
            imports = ", ".join(module_parts[1:])

            # Check if we already have this import from the extraction
            already_added = any(
                module == import_from.replace("backend.", "")
                and all(imp.strip() in import_what for imp in imports.split(","))
                for import_from, import_what in backend_imports
            )

            if not already_added:
                hybrid_imports.append(f"from {module} import {imports}")
                hybrid_backend_imports.append(f"from backend.{module} import {imports}")

        # Format the hybrid import section
        hybrid_section = HYBRID_IMPORT_TEMPLATE.format(
            imports="\n    ".join(hybrid_imports),
            backend_imports="\n    ".join(hybrid_backend_imports),
        )

        # Get all imports currently in the file
        import_pattern = r"^(from .+? import .+?$|import .+?$)"
        re.findall(import_pattern, content, re.MULTILINE)

        # Remove backend imports that will be in hybrid section
        backend_import_patterns = []
        for import_from, _ in backend_imports:
            pattern = re.escape(f"from {import_from} import")
            backend_import_patterns.append(pattern)

        # Create pattern to match all backend imports
        if backend_import_patterns:
            backend_pattern = "|".join(backend_import_patterns)
            content = re.sub(
                rf"^({backend_pattern}).*?$", "", content, flags=re.MULTILINE
            )

        # Find where to insert hybrid imports
        # After the last standard import or at the beginning after the docstring
        std_imports = re.findall(r"^(import .+?$)", content, re.MULTILINE)
        from_imports = re.findall(
            r"^(from (?!backend).+? import .+?$)", content, re.MULTILINE
        )

        # Add standard imports if needed
        for std_import in STANDARD_IMPORTS:
            if not any(std_import in imp for imp in std_imports + from_imports):
                if std_import.startswith("from"):
                    imports_to_add.append(std_import)
                else:
                    imports_to_add.insert(0, std_import)

        # Add FastAPI imports if needed
        for fastapi_import in FASTAPI_IMPORTS:
            if not any(fastapi_import in imp for imp in from_imports):
                imports_to_add.append(fastapi_import)

        # If there are imports in the file
        if std_imports or from_imports:
            # Find a good place to insert the hybrid section and additional imports
            last_std_import = std_imports[-1] if std_imports else None
            last_from_import = from_imports[-1] if from_imports else None

            if last_from_import:
                last_import = last_from_import
            elif last_std_import:
                last_import = last_std_import
            else:
                last_import = None

            if last_import:
                # Add after the last import
                if imports_to_add:
                    add_imports = "\n".join(imports_to_add)
                    content = content.replace(
                        last_import, f"{last_import}\n{add_imports}"
                    )

                # Now find the updated last import and add hybrid section
                all_imports = re.findall(import_pattern, content, re.MULTILINE)
                last_import = all_imports[-1] if all_imports else None

                if last_import:
                    content = content.replace(
                        last_import, f"{last_import}\n{hybrid_section}"
                    )
            else:
                # No imports found, add after docstring
                docstring_end = re.search(r'(""".+?"""\n)', content, re.DOTALL)
                if docstring_end:
                    add_imports = "\n".join(imports_to_add)
                    content = content.replace(
                        docstring_end.group(0),
                        f"{docstring_end.group(0)}\n{add_imports}\n{hybrid_section}\n",
                    )
                else:
                    # No docstring, add at beginning
                    add_imports = "\n".join(imports_to_add)
                    content = f"{add_imports}\n{hybrid_section}\n{content}"
        else:
            # No imports in file, add after docstring or at beginning
            docstring_end = re.search(r'(""".+?"""\n)', content, re.DOTALL)
            if docstring_end:
                add_imports = "\n".join(imports_to_add)
                content = content.replace(
                    docstring_end.group(0),
                    f"{docstring_end.group(0)}\n{add_imports}\n{hybrid_section}\n",
                )
            else:
                # No docstring, add at beginning
                add_imports = "\n".join(imports_to_add)
                content = f"{add_imports}\n{hybrid_section}\n{content}"

        return content

    def extract_backend_imports(self, content):
        """Extract backend imports from the content"""
        backend_imports = []

        # Find all 'from backend.X import Y' statements
        import_pattern = r"from\s+(backend\.\S+)\s+import\s+([^#\n]+)"
        matches = re.findall(import_pattern, content)

        for module, imports in matches:
            backend_imports.append((module, imports.strip()))

        return backend_imports

    def identify_additional_imports(self, content, file_path):
        """Identify imports that should be added based on file content"""
        additional_imports = []

        # Check for common usages and add imports as needed
        if "shutil" in content and "import shutil" not in content:
            additional_imports.append("import shutil")

        if "mimetypes" in content and "import mimetypes" not in content:
            additional_imports.append("import mimetypes")

        if re.search(r"\basyncio\.", content) and "import asyncio" not in content:
            additional_imports.append("import asyncio")

        # Check for FastAPI specific imports
        if "Form(" in content and "Form" not in content:
            additional_imports.append("from fastapi import Form")

        if "File(" in content and "File" not in content:
            additional_imports.append("from fastapi import File")

        if "UploadFile" in content and "UploadFile" not in content:
            additional_imports.append("from fastapi import UploadFile")

        if "BackgroundTasks" in content and "BackgroundTasks" not in content:
            additional_imports.append("from fastapi import BackgroundTasks")

        return additional_imports

    def print_summary(self):
        """Print a summary of the operations performed"""
        print("\n" + "=" * 60)
        print(f"{self.action_prefix}Import Standardization Summary:")
        print(f"  Files processed: {self.files_processed}")
        print(f"  Files modified:  {self.files_modified}")
        print("=" * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Standardize imports in API modules")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without modifying files"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed information"
    )
    parser.add_argument("--module", help="Process only the specified module")

    args = parser.parse_args()

    # Ensure we're running from the project root
    if not os.path.exists("backend/api"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(os.path.join(script_dir, "../.."))

    if not os.path.exists("backend/api"):
        print(
            "Error: Could not find backend/api directory. Please run this script from the project root."
        )
        return 1

    standardizer = ImportStandardizer(dry_run=args.dry_run, verbose=args.verbose)

    if args.module:
        # Process a single module
        module_path = os.path.join("backend/api", f"{args.module}.py")
        if os.path.exists(module_path):
            standardizer.process_file(module_path)
        else:
            print(f"Error: Module {args.module}.py not found in backend/api")
            return 1
    else:
        # Process all API modules
        standardizer.process_directory("backend/api")

    return 0


if __name__ == "__main__":
    sys.exit(main())
