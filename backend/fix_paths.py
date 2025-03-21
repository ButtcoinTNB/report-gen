"""
Path fixing module for making imports work in both development and production.
This should be imported at the top of main.py.
"""

import os
import sys
import importlib.util
from pathlib import Path

def fix_python_path():
    """
    Fix Python path to make imports work in both development and production.
    In production (Render), the app runs from inside the backend directory.
    """
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    # Check if we're inside the backend directory
    backend_dir = Path(current_dir)
    if backend_dir.name == 'backend':
        print(f"Backend directory: {backend_dir}")
        
        # Add parent directory to path if needed
        parent_dir = str(backend_dir.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            print(f"Python path fixed for deployment. sys.path: {sys.path}")
    
    # Verify it worked
    try:
        importlib.util.find_spec('backend')
        print("Successfully imported fix_paths")
        return True
    except ImportError:
        print("WARNING: Could not import 'backend' module after path fix!")
        return False
        
# Auto-run the fix when imported
fix_python_path() 