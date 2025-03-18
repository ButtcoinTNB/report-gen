import sys
import os

# Add the root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Try to import app from backend.main
    from backend.main import app
    print("Successfully imported app from backend.main")
except ModuleNotFoundError:
    # If that fails, try a different approach for Render
    print("Failed to import from backend.main directly, adjusting path...")
    
    # Check if we're in a directory that has backend subdirectory
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    if os.path.isdir(backend_dir):
        sys.path.insert(0, backend_dir)
        
        # Now try to import
        try:
            from main import app
            print("Successfully imported app from backend/main.py")
        except ModuleNotFoundError as e:
            print(f"Failed to import app: {e}")
            raise
    else:
        print("Could not find backend directory")
        raise ImportError("Could not import app from any location")

# This file serves as the main entry point for the application
# The app is defined in the backend.main module 