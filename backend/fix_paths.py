"""
Fix Python import paths for Render deployment

This module should be imported at the beginning of main.py to ensure
proper module resolution and package recognition.
"""

import os
import sys
import importlib
import types

def fix_python_path():
    """
    Adjust Python path to make imports work correctly in both local development
    and production environments like Render.
    """
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    # Get the directory of this file
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Backend directory: {backend_dir}")
    
    # Add backend_dir to sys.path if not already there
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
        print(f"Added backend directory to Python path: {backend_dir}")
    
    # Create __init__.py files in key directories to ensure they're recognized as packages
    ensure_init_files(backend_dir)
    
    return backend_dir

def ensure_init_files(start_dir):
    """Create missing __init__.py files in important subdirectories"""
    key_dirs = ['api', 'utils', 'services', 'models']
    created = 0
    
    for dir_name in key_dirs:
        dir_path = os.path.join(start_dir, dir_name)
        if os.path.isdir(dir_path):
            init_file = os.path.join(dir_path, '__init__.py')
            if not os.path.exists(init_file):
                try:
                    with open(init_file, 'w') as f:
                        f.write('# Auto-generated __init__.py file for module imports\n')
                    created += 1
                    print(f"Created missing __init__.py in {dir_path}")
                except Exception as e:
                    print(f"Failed to create __init__.py in {dir_path}: {str(e)}")
    
    return created

# Run the function when this module is imported
backend_dir = fix_python_path()
print(f"Python path fixed for deployment. sys.path: {sys.path}") 