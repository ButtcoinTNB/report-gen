"""
Path fixing module for making imports work in both development and production.
This should be imported at the top of main.py.
"""

import importlib.util
import os
import sys
from pathlib import Path


def is_production():
    """Determine if we're running in production (Render) environment."""
    # Render sets this environment variable
    return os.environ.get("RENDER") == "true"


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
    if backend_dir.name == "backend":
        print(f"Backend directory: {backend_dir}")

        # Add parent directory to path if needed
        parent_dir = str(backend_dir.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            print(f"Added parent directory to sys.path: {parent_dir}")

        # In production, we don't need to look for 'backend.module'
        # because we're already in the backend directory
        if is_production():
            print("Running in production (Render) environment.")
            print("Import paths should NOT use 'backend.' prefix.")

            # CRITICAL: Make sure the current directory is in sys.path
            # This ensures modules like 'utils' can be imported directly
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
                print(f"Added current directory to sys.path: {current_dir}")

            # Also add utils, api, and other key directories directly
            utils_dir = os.path.join(current_dir, "utils")
            if os.path.exists(utils_dir) and utils_dir not in sys.path:
                sys.path.insert(0, utils_dir)
                print(f"Added utils directory to sys.path: {utils_dir}")

            api_dir = os.path.join(current_dir, "api")
            if os.path.exists(api_dir) and api_dir not in sys.path:
                sys.path.insert(0, api_dir)
                print(f"Added api directory to sys.path: {api_dir}")
        else:
            print("Running in local development environment from backend directory.")
            print(
                "Import paths should still use 'backend.' prefix in non-entry-point modules."
            )
    else:
        print(f"Not in backend directory. Current directory: {backend_dir.name}")
        print("Running in local development environment.")
        print("Import paths should use 'backend.' prefix.")

        # Ensure backend directory is in path for local development
        if backend_dir.parent.name == "backend":
            # We're in a subdirectory of backend
            root_dir = str(backend_dir.parent.parent)
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)

    # For debugging: Print the full sys.path
    print(f"Full Python sys.path: {sys.path}")

    # Verify it worked
    try:
        importlib.util.find_spec("backend")
        print("Successfully imported backend module")

        if is_production():
            # In production, also verify we can import utils directly
            try:
                importlib.util.find_spec("utils")
                print("Successfully verified utils module can be imported")
            except ImportError:
                print(
                    "WARNING: Could not import 'utils' module! Path fixing may not be sufficient."
                )

        return True
    except ImportError:
        print("WARNING: Could not import 'backend' module after path fix!")
        return False


# Auto-run the fix when imported
fix_python_path()
