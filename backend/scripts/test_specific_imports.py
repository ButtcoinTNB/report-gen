#!/usr/bin/env python3
"""
Test script to verify imports between specific modules to confirm
the circular dependency issues have been resolved.
"""

import sys
import os
import importlib
import traceback
from typing import Optional

# Add backend directory to Python path
# Get the absolute path of the parent directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
    print(f"Added {backend_dir} to Python path")

def test_import(module_name: str) -> bool:
    """
    Test importing a module and report success or failure
    
    Args:
        module_name: The name of the module to test import
        
    Returns:
        True if import successful, False otherwise
    """
    print(f"Testing import: {module_name}")
    try:
        importlib.import_module(module_name)
        print(f"✅ Successfully imported {module_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to import {module_name}: {str(e)}")
        traceback.print_exc()
        return False

def main() -> Optional[int]:
    """Main test function"""
    
    # Test these two modules individually
    print("\n=== Testing Individual Modules ===")
    test_import("utils.error_handler")
    test_import("services.docx_formatter")
    
    # Test import order that would previously cause circular imports
    print("\n=== Testing Import Order 1 ===")
    try:
        # Clear modules first to ensure clean test
        if 'utils.error_handler' in sys.modules:
            del sys.modules['utils.error_handler']
        if 'services.docx_formatter' in sys.modules:
            del sys.modules['services.docx_formatter']
            
        # Using __import__ instead of direct import statements to avoid linter warnings
        # about unused imports
        __import__('utils.error_handler')
        __import__('services.docx_formatter')
        print("✅ Successfully imported both modules in order: utils.error_handler then services.docx_formatter")
    except Exception as e:
        print(f"❌ Failed to import both modules in order: {str(e)}")
        traceback.print_exc()
    
    print("\n=== Testing Import Order 2 ===")
    try:
        # Clear modules first to ensure clean test
        if 'utils.error_handler' in sys.modules:
            del sys.modules['utils.error_handler']
        if 'services.docx_formatter' in sys.modules:
            del sys.modules['services.docx_formatter']
            
        # Using __import__ instead of direct import statements
        __import__('services.docx_formatter')
        __import__('utils.error_handler')
        print("✅ Successfully imported both modules in order: services.docx_formatter then utils.error_handler")
    except Exception as e:
        print(f"❌ Failed to import both modules in order: {str(e)}")
        traceback.print_exc()
    
    print("\n=== Test Complete ===")
    return None

if __name__ == "__main__":
    sys.exit(main() or 0) 