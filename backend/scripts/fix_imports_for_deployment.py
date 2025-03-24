#!/usr/bin/env python
"""
Script to fix imports in backend Python files for deployment compatibility.
This ensures the code works in both local development and production.

Usage:
    python backend/scripts/fix_imports_for_deployment.py

The script:
1. Makes imports in main.py and router modules use relative imports (from api import...)
2. Fixes other modules to use absolute or relative imports based on where they are imported
"""

import os
import re
from pathlib import Path

# Define the backend directory
BACKEND_DIR = Path(__file__).parent.parent.absolute()
ROOT_DIR = BACKEND_DIR.parent

# Regular expression to find imports
IMPORT_PATTERN = re.compile(
    r"^(from|import)\s+(backend\.)?([a-zA-Z0-9_.]+)\s*(import\s+|as\s+|$)", re.MULTILINE
)

# Files that should use relative imports
RELATIVE_IMPORT_FILES = [
    "main.py",
    os.path.join("api", "upload.py"),
    os.path.join("api", "generate.py"),
    os.path.join("api", "format.py"),
    os.path.join("api", "edit.py"),
    os.path.join("api", "download.py"),
]


def fix_imports_in_file(file_path, force_relative=False):
    """Fix imports in a single file."""
    with open(file_path, "r") as f:
        content = f.read()

    # Track if any changes were made
    changes_made = False

    # Find all imports and fix them
    def replace_import(match):
        nonlocal changes_made

        import_type = match.group(1)  # 'from' or 'import'
        has_backend_prefix = (
            match.group(2) is not None
        )  # Whether the import already has 'backend.'
        module_path = match.group(3)  # The module path
        rest_of_line = match.group(4)  # The rest of the import line

        # Skip standard library and third-party modules
        if "." not in module_path or module_path.split(".")[0] not in [
            "api",
            "utils",
            "models",
            "services",
            "config",
        ]:
            return match.group(0)

        # Handle based on whether to use relative or absolute imports
        if force_relative:
            # Remove 'backend.' prefix if it exists
            if has_backend_prefix:
                changes_made = True
                return f"{import_type} {module_path} {rest_of_line}"
            return match.group(0)
        else:
            # Add 'backend.' prefix if it doesn't exist
            if not has_backend_prefix:
                changes_made = True
                return f"{import_type} backend.{module_path} {rest_of_line}"
            return match.group(0)

    updated_content = IMPORT_PATTERN.sub(replace_import, content)

    # Only write back if we made changes
    if changes_made:
        with open(file_path, "w") as f:
            f.write(updated_content)
        return True

    return False


def scan_directory_and_fix_imports():
    """Scan all Python files in the backend directory and fix imports."""
    fixed_files = []

    for root, _, files in os.walk(BACKEND_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, BACKEND_DIR)

                # Determine whether to use relative imports for this file
                force_relative = relative_path in RELATIVE_IMPORT_FILES

                # Fix imports in this file
                if fix_imports_in_file(file_path, force_relative):
                    fixed_files.append(relative_path)

    return fixed_files


if __name__ == "__main__":
    print(f"Scanning backend directory: {BACKEND_DIR}")
    fixed_files = scan_directory_and_fix_imports()

    if fixed_files:
        print(f"Fixed imports in {len(fixed_files)} files:")
        for file in fixed_files:
            print(f" - {file}")
        print("\nAll imports have been updated for deployment compatibility.")
    else:
        print("No files needed import fixes.")
