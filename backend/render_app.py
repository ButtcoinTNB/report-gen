"""
Render deployment entry point - ensures paths are fixed before any imports.
This file should be used only for Render deployment.

Usage on Render:
    python -m uvicorn render_app:app --host 0.0.0.0 --port $PORT
"""

# First, set up the Python path properly
import os
import sys
from pathlib import Path

# 1. Critical: Make the current directory searchable for modules
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    print(f"[RENDER] Added current directory to sys.path: {current_dir}")

# 2. Add key directories to path directly
for subdir in ['utils', 'api', 'services', 'models', 'config', 'schemas']:
    subdir_path = os.path.join(current_dir, subdir)
    if os.path.isdir(subdir_path) and subdir_path not in sys.path:
        sys.path.insert(0, subdir_path)
        print(f"[RENDER] Added {subdir} directory to sys.path: {subdir_path}")

# 3. Add parent directory too
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    print(f"[RENDER] Added parent directory to sys.path: {parent_dir}")

# Print the Python path for debugging
print(f"[RENDER] Python sys.path: {sys.path}")

# Ensure important directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("generated_reports", exist_ok=True)

# Create necessary __init__.py files
for dir_name in ['api', 'utils', 'services', 'models', 'config']:
    dir_path = os.path.join(current_dir, dir_name)
    if os.path.isdir(dir_path):
        init_file = os.path.join(dir_path, '__init__.py')
        if not os.path.exists(init_file):
            try:
                with open(init_file, 'w') as f:
                    f.write('# Auto-generated __init__.py file\n')
                print(f"[RENDER] Created {init_file}")
            except Exception as e:
                print(f"[RENDER] Failed to create {init_file}: {str(e)}")

# Now verify that modules can be imported
try:
    import utils
    print("[RENDER] Successfully imported utils module")
    import utils.logger
    print("[RENDER] Successfully imported utils.logger module")
except ImportError as e:
    print(f"[RENDER] ERROR: {str(e)}")
    # Raise a clear error
    raise ImportError(f"Critical import error: {str(e)}. Python path is: {sys.path}") from e

# Only import the app after paths are fixed
try:
    from main import app
    print("[RENDER] Successfully imported app from main")
except ImportError as e:
    print(f"[RENDER] ERROR importing app from main: {str(e)}")
    raise

# Expose the app for uvicorn
print("[RENDER] Render entry point initialized successfully!") 