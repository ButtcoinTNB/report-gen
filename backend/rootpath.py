"""
Utility module to ensure Python can find all necessary modules
regardless of whether the app is run from the project root or the backend directory.
"""

import os
import sys


def ensure_root_in_path():
    """
    Add the project root to the Python path if it's not already there.
    This ensures proper module imports work correctly.
    """
    # Get the absolute path to the backend directory (where this file resides)
    backend_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the absolute path to the project root (parent of backend dir)
    project_root = os.path.dirname(backend_dir)

    # Check whether we're running from the backend directory or project root
    running_from_backend = os.path.basename(os.getcwd()) == "backend"

    # Add paths based on where we're running from
    if running_from_backend:
        # We're running from backend/ so this is our effective root
        # Add backend to path to ensure imports work
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
            print(f"Added backend directory to Python path: {backend_dir}")

        # Add parent directory for accessing project root resources
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            print(f"Added project root to Python path: {project_root}")
    else:
        # We're running from project root
        # Make sure project root is in path
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            print(f"Added project root to Python path: {project_root}")

    print(f"Running from: {os.getcwd()}")
    print(f"Backend dir: {backend_dir}")
    print(f"Project root: {project_root}")

    return project_root, backend_dir
