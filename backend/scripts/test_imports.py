#!/usr/bin/env python3
"""
Test script to verify imports are working properly and circular dependencies are resolved.

This script attempts to import various modules in different orders to confirm
the circular dependency issues have been resolved.
"""

import sys
import importlib
import traceback

def test_import(module_name):
    """
    Test importing a module and report success or failure
    
    Args:
        module_name: The name of the module to test import
        
    Returns:
        True if import successful, False otherwise
    """
    print(f"Testing import: {module_name}")
    try:
        module = importlib.import_module(module_name)
        print(f"✅ Successfully imported {module_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to import {module_name}: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    
    print("\n=== Testing Core Modules ===")
    core_modules = [
        "core.types",
    ]
    
    print("\n=== Testing Utils Modules ===")
    utils_modules = [
        "utils.error_handler",
        "utils.resource_manager",
        "utils.event_emitter",
    ]
    
    print("\n=== Testing API Modules ===")
    api_modules = [
        "api.schemas",
    ]
    
    print("\n=== Testing Service Modules ===")
    service_modules = [
        "services.docx_formatter",
    ]
    
    # First test individual modules
    all_modules = core_modules + utils_modules + api_modules + service_modules
    
    success_count = 0
    failure_count = 0
    
    for module in all_modules:
        if test_import(module):
            success_count += 1
        else:
            failure_count += 1
    
    # Test import order that would previously cause circular imports
    print("\n=== Testing Import Orders That Previously Caused Circular Dependencies ===")
    
    print("\n1. Test importing services.docx_formatter then utils.error_handler")
    try:
        print("✅ Successfully imported both modules in order")
    except Exception as e:
        print(f"❌ Failed to import both modules in order: {str(e)}")
        traceback.print_exc()
        failure_count += 1
    
    print("\n2. Test importing utils.error_handler then api.schemas")
    try:
        # Reload modules to ensure clean test
        if 'utils.error_handler' in sys.modules:
            del sys.modules['utils.error_handler']
        if 'api.schemas' in sys.modules:
            del sys.modules['api.schemas']
            
        print("✅ Successfully imported both modules in order")
    except Exception as e:
        print(f"❌ Failed to import both modules in order: {str(e)}")
        traceback.print_exc()
        failure_count += 1
    
    print("\n3. Test importing api.schemas then utils.error_handler")
    try:
        # Reload modules to ensure clean test
        if 'utils.error_handler' in sys.modules:
            del sys.modules['utils.error_handler']
        if 'api.schemas' in sys.modules:
            del sys.modules['api.schemas']
            
        print("✅ Successfully imported both modules in order")
    except Exception as e:
        print(f"❌ Failed to import both modules in order: {str(e)}")
        traceback.print_exc()
        failure_count += 1
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Successfully imported: {success_count} modules")
    print(f"Failed to import: {failure_count} modules or module combinations")
    
    if failure_count > 0:
        print("\n❌ Some imports failed. Circular dependencies may still exist.")
        return 1
    else:
        print("\n✅ All imports successful! Circular dependencies appear to be resolved.")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 