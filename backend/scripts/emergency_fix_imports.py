#!/usr/bin/env python
"""
Emergency script to fix imports in API modules to use absolute paths with backend prefix.
This script directly targets the files that need to be fixed for deployment.

Usage:
    python backend/scripts/emergency_fix_imports.py
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
    """Fix imports in a file to use backend prefix."""
    print(f"Fixing imports in {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fixed content with backend prefix for internal imports
    # Regex to match imports not starting with backend
    fixed_content = re.sub(
        r'from (api|utils|services|models|config|db|schemas)\.', 
        r'from backend.\1.', 
        content
    )
    
    # Also fix import statements without from
    fixed_content = re.sub(
        r'import (api|utils|services|models|config|db|schemas)\.', 
        r'import backend.\1.', 
        fixed_content
    )
    
    # Write back the fixed content
    with open(file_path, 'w') as f:
        f.write(fixed_content)
    
    return content != fixed_content  # Return True if changes were made

def main():
    """Main function to fix imports in all API files."""
    print("Starting emergency import fixes...")
    
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