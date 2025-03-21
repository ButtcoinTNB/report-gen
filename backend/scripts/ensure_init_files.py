#!/usr/bin/env python
"""
Ensure __init__.py Files

This script ensures that all subdirectories within the backend have proper __init__.py files,
which is critical for Python to recognize them as packages and enable imports to work correctly.

Usage:
    python scripts/ensure_init_files.py

This should be run before deployment to ensure all packages can be imported correctly.
"""

import os
import sys
from pathlib import Path

def ensure_init_files(start_dir):
    """
    Create __init__.py files in all subdirectories of start_dir if they don't exist.
    
    Args:
        start_dir: The directory to start from
    
    Returns:
        int: Number of __init__.py files created
    """
    count = 0
    
    # Get the absolute path of the start directory
    start_path = os.path.abspath(start_dir)
    print(f"Ensuring __init__.py files exist in subdirectories of {start_path}")
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(start_path):
        # Skip hidden directories and virtual environments
        if any(part.startswith('.') for part in root.split(os.sep)) or 'venv' in root or '__pycache__' in root:
            continue
        
        # Check if this directory is a Python package (should have __init__.py)
        init_file = os.path.join(root, '__init__.py')
        if not os.path.exists(init_file):
            try:
                # Create an empty __init__.py file
                with open(init_file, 'w') as f:
                    f.write('# Auto-generated __init__.py file for module imports\n')
                count += 1
                print(f"Created missing {init_file}")
            except Exception as e:
                print(f"Error creating {init_file}: {str(e)}")
    
    return count

if __name__ == "__main__":
    # Determine the backend directory
    current_file = os.path.abspath(__file__)
    scripts_dir = os.path.dirname(current_file)
    backend_dir = os.path.dirname(scripts_dir)
    
    print(f"Current file: {current_file}")
    print(f"Scripts directory: {scripts_dir}")
    print(f"Backend directory: {backend_dir}")
    
    # Ensure init files in the backend directory
    created = ensure_init_files(backend_dir)
    
    print(f"Created {created} missing __init__.py files")
    print("Done! The backend should now be properly configured for imports.")
    
    # Exit with success
    sys.exit(0) 