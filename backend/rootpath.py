"""
Utility module to ensure Python can find all necessary modules
regardless of whether the app is run from the project root or the backend directory.
"""

import os
import sys

def ensure_root_in_path():
    """
    Add the project root to the Python path if it's not already there.
    This ensures 'backend' can be imported by Python.
    """
    # Get the absolute path to the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get the absolute path to the project root
    project_root = os.path.dirname(backend_dir)
    
    # Add the project root to the Python path if not already there
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added project root to Python path: {project_root}")
        
    # For good measure, also add the backend dir
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
        print(f"Added backend directory to Python path: {backend_dir}")
    
    return project_root, backend_dir 