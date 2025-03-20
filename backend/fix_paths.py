"""
Fix Python import paths for Render deployment

This module should be imported at the beginning of main.py to ensure
both relative imports and absolute imports with the 'backend' prefix work properly.
"""

import os
import sys

def fix_python_path():
    """
    Adjust Python path to make both relative and prefixed imports work.
    This handles the specific path issues on Render deployment.
    """
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    # Get the directory of this file
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Backend directory: {backend_dir}")
    
    # Get the project root (parent of backend dir)
    project_root = os.path.dirname(backend_dir)
    print(f"Project root: {project_root}")
    
    # Add the project root and backend dir to the path if not already there
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added project root to Python path: {project_root}")
    
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
        print(f"Added backend directory to Python path: {backend_dir}")
    
    # Create a 'backend' directory in sys.modules if it doesn't exist
    # This allows 'from backend.X import Y' to work as if importing from the actual backend directory
    if 'backend' not in sys.modules:
        import types
        backend_module = types.ModuleType('backend')
        sys.modules['backend'] = backend_module
        print("Created 'backend' module in sys.modules")
    
    # Return the paths so they can be used elsewhere
    return project_root, backend_dir

# Run the function when this module is imported
project_root, backend_dir = fix_python_path()
print(f"Python path fixed for deployment. sys.path: {sys.path}") 