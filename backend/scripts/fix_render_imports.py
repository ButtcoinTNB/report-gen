#!/usr/bin/env python
"""
Render deployment import fix script.

This script removes the 'backend.' prefix from imports when deploying to Render,
since the root directory in Render is already set to the 'backend' folder.

Usage:
    python backend/scripts/fix_render_imports.py
"""

import os
import re
from pathlib import Path

# Define the backend directory
BACKEND_DIR = Path(__file__).parent.parent.absolute()

# Files to fix
API_FILES = [
    os.path.join(BACKEND_DIR, "api", "upload.py"),
    os.path.join(BACKEND_DIR, "api", "generate.py"),
    os.path.join(BACKEND_DIR, "api", "format.py"),
    os.path.join(BACKEND_DIR, "api", "edit.py"),
    os.path.join(BACKEND_DIR, "api", "download.py"),
]

def fix_file_imports(file_path):
    """Fix imports in a file by removing the backend prefix."""
    print(f"Fixing imports in {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove 'backend.' prefix from imports
    fixed_content = re.sub(
        r'from backend\.(api|utils|services|models|config|db|schemas)\.', 
        r'from \1.', 
        content
    )
    
    # Also fix import statements without from
    fixed_content = re.sub(
        r'import backend\.(api|utils|services|models|config|db|schemas)\.', 
        r'import \1.', 
        fixed_content
    )
    
    # Write back the fixed content
    with open(file_path, 'w') as f:
        f.write(fixed_content)
    
    return content != fixed_content  # Return True if changes were made

def main():
    """Main function to fix imports in all API files."""
    print("Starting Render deployment import fixes...")
    
    fixed_files = []
    for file_path in API_FILES:
        if os.path.exists(file_path):
            if fix_file_imports(file_path):
                fixed_files.append(os.path.basename(file_path))
        else:
            print(f"Warning: File {file_path} not found!")
    
    if fixed_files:
        print(f"\nSuccessfully fixed imports in {len(fixed_files)} files:")
        for file in fixed_files:
            print(f"- {file}")
        print("\nYou should now be able to deploy the application successfully.")
    else:
        print("No files needed fixing.")

if __name__ == "__main__":
    main() 