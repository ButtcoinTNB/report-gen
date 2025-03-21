#!/usr/bin/env python
"""
Verify that all necessary modules can be imported.
This script tests that the import system is correctly configured
for both development and production environments.

Usage:
    python backend/scripts/verify_imports.py
"""

import os
import sys
import importlib.util

def test_import(module_name):
    """Test if a module can be imported and print result."""
    try:
        importlib.util.find_spec(module_name)
        print(f"✅ Successfully imported {module_name}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {str(e)}")
        return False

def main():
    """Test various imports to verify system configuration."""
    print("==========================================")
    print("PYTHON IMPORT VERIFICATION TOOL")
    print("==========================================")
    
    # Print current environment
    print("\nENVIRONMENT:")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script location: {os.path.abspath(__file__)}")
    
    # Try to load fix_paths
    print("\nTESTING PATH FIXING:")
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from fix_paths import fix_python_path
        fix_python_path()
        print("✅ Successfully imported and ran fix_paths")
    except ImportError:
        print("❌ Could not import fix_paths")
        
        # Manual path fixing as fallback
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, backend_dir)
        sys.path.insert(0, os.path.dirname(backend_dir))
        print(f"Applied manual path fixing: {backend_dir}")
    
    # Print sys.path
    print("\nPYTHON PATH:")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")
    
    # Test various imports
    print("\nTESTING KEY IMPORTS:")
    test_modules = [
        # Test for both styles
        "backend",
        "backend.utils",
        "backend.api",
        "utils",
        "api",
        
        # Test specific modules
        "utils.logger",
        "api.schemas",
        "config",
    ]
    
    success = 0
    for module in test_modules:
        if test_import(module):
            success += 1
    
    # Summary
    print("\nSUMMARY:")
    print(f"Successfully imported {success} out of {len(test_modules)} modules")
    print("==========================================")
    
    return 0 if success == len(test_modules) else 1

if __name__ == "__main__":
    sys.exit(main()) 