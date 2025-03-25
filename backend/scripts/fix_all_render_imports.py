#!/usr/bin/env python
"""
Enhanced Render deployment import fix script.

This script removes the 'backend.' prefix from ALL imports when deploying to Render,
since the root directory in Render is already set to the 'backend' folder.

Usage:
    python backend/scripts/fix_all_render_imports.py
"""

import os
import re
from pathlib import Path

# Define the backend directory
BACKEND_DIR = Path(__file__).parent.parent.absolute()


def fix_file_imports(file_path):
    """Fix imports in a file by removing the backend prefix."""
    print(f"Fixing imports in {os.path.relpath(file_path, BACKEND_DIR)}")

    with open(file_path, "r") as f:
        content = f.read()

    # Remove 'backend.' prefix from imports
    fixed_content = re.sub(
        r"from backend\.(api|utils|services|models|config|db|schemas|middleware|ai|tests|docs|scripts|templates|reference_reports)\.",
        r"from \1.",
        content,
    )

    # Also fix import statements without from
    fixed_content = re.sub(
        r"import backend\.(api|utils|services|models|config|db|schemas|middleware|ai|tests|docs|scripts|templates|reference_reports)\.",
        r"import \1.",
        fixed_content,
    )

    # Simple module imports (without submodules)
    fixed_content = re.sub(
        r"from backend\.(api|utils|services|models|config|db|schemas|middleware|ai|tests|docs|scripts|templates|reference_reports)(\s+import|\s+as)",
        r"from \1\2",
        fixed_content,
    )

    fixed_content = re.sub(
        r"import backend\.(api|utils|services|models|config|db|schemas|middleware|ai|tests|docs|scripts|templates|reference_reports)(\s+as|\s*$)",
        r"import \1\2",
        fixed_content,
    )

    # Write back the fixed content
    with open(file_path, "w") as f:
        f.write(fixed_content)

    return content != fixed_content  # Return True if changes were made


def scan_directory_and_fix_imports():
    """Scan all Python files in the backend directory and fix imports."""
    fixed_files = []

    for root, _, files in os.walk(BACKEND_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                if fix_file_imports(file_path):
                    relative_path = os.path.relpath(file_path, BACKEND_DIR)
                    fixed_files.append(relative_path)

    return fixed_files


def main():
    """Main function to fix imports in all Python files."""
    print("Starting Render deployment import fixes for ALL Python files...")

    fixed_files = scan_directory_and_fix_imports()

    if fixed_files:
        print(f"\nSuccessfully fixed imports in {len(fixed_files)} files:")
        for file in fixed_files[:20]:  # Show first 20 files
            print(f"- {file}")
        
        if len(fixed_files) > 20:
            print(f"... and {len(fixed_files) - 20} more files")
            
        print("\nYou should now be able to deploy the application successfully.")
    else:
        print("No files needed fixing.")


if __name__ == "__main__":
    main() 