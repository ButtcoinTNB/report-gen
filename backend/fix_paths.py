"""
Path fixing module for making imports work in both development and production.
This should be imported at the top of main.py.
"""

import os
import sys
import importlib.util
from pathlib import Path

def is_production():
    """Determine if we're running in production (Render) environment."""
    # Render sets this environment variable
    return os.environ.get('RENDER') == 'true'

def fix_python_path():
    """
    Fix Python path to make imports work in both development and production.
    
    In local development:
    - Project structure is /project_root/backend/
    - Running from project_root
    - Imports should use 'backend.module.submodule'
    
    In production (Render):
    - Project structure is /opt/render/project/src/backend/
    - Running from inside backend directory
    - Imports should use 'module.submodule' without 'backend.' prefix
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
            
        # In production, we don't need to look for 'backend.module'
        # because we're already in the backend directory
        if is_production():
            print("Running in production (Render) environment.")
            print("Import paths should NOT use 'backend.' prefix.")
        else:
            print("Running in local development environment from backend directory.")
            print("Import paths should still use 'backend.' prefix in non-entry-point modules.")
    else:
        print(f"Not in backend directory. Current directory: {backend_dir.name}")
        print("Running in local development environment.")
        print("Import paths should use 'backend.' prefix.")
        
        # Ensure backend directory is in path for local development
        if backend_dir.parent.name == 'backend':
            # We're in a subdirectory of backend
            root_dir = str(backend_dir.parent.parent)
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
    
    # Verify it worked
    try:
        importlib.util.find_spec('backend')
        print("Successfully imported backend module")
        return True
    except ImportError:
        print("WARNING: Could not import 'backend' module after path fix!")
        return False
        
# Auto-run the fix when imported
fix_python_path() 