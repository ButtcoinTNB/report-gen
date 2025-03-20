#!/usr/bin/env python
"""
Test script for path validation security functions.
Tests various inputs including directory traversal attempts.

Usage:
    python test_path_validation.py
"""

import os
import sys
from typing import Dict, List, Tuple
from pathlib import Path

# Add the project root to the Python path to import utils
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the functions we want to test
try:
    from backend.utils.storage import validate_path, get_safe_file_path
except ImportError:
    print("Could not import from backend.utils.storage.")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)


def run_test_case(case_name: str, base_dir: str, test_path: str, expected_valid: bool) -> bool:
    """Run a single test case and return whether it passed."""
    print(f"\n\033[1mTest Case: {case_name}\033[0m")
    print(f"Base Directory: {base_dir}")
    print(f"Test Path: {test_path}")
    print(f"Expected Valid: {expected_valid}")
    
    try:
        is_valid, validated_path = validate_path(test_path, base_dir)
        print(f"Result: {'Valid' if is_valid else 'Invalid'}")
        if validated_path:
            print(f"Validated Path: {validated_path}")
        
        # Check if the result matches our expectation
        if is_valid == expected_valid:
            print("\033[92mPASS\033[0m")
            return True
        else:
            print("\033[91mFAIL\033[0m")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\033[91mFAIL (exception)\033[0m")
        return False


def run_test_cases() -> None:
    """Run all test cases and report results."""
    # Create a temporary test directory for our tests
    test_base_dir = os.path.join(os.getcwd(), "tmp", "path_test")
    os.makedirs(test_base_dir, exist_ok=True)
    
    # Test cases: (name, path, expected_valid)
    test_cases = [
        # Valid cases
        ("Simple valid path", "file.txt", True),
        ("Valid path with directory", "dir/file.txt", True),
        ("Valid UUID filename", "550e8400-e29b-41d4-a716-446655440000.docx", True),
        
        # Directory traversal attempts - these should be invalid
        ("Simple traversal", "../file.txt", False),
        ("Double traversal", "../../file.txt", False),
        ("Nested traversal", "dir/../../../file.txt", False),
        ("Absolute path", "/etc/passwd", False),
        ("Encoded traversal", "..%2Ffile.txt", False),
        ("URL encoded traversal", "%2e%2e%2ffile.txt", False),
        ("Null byte injection", "file.txt\0.jpg", False),
        
        # Edge cases
        ("Empty path", "", False),
        ("Only dots", "...", True),  # This is a valid filename, not traversal
        ("Path with special chars", "file-!@#$%^&*().txt", True),
        
        # UUID validation cases
        ("Valid UUID format", "550e8400-e29b-41d4-a716-446655440000", True),
        ("Invalid UUID format", "not-a-valid-uuid", False),
        ("UUID with path traversal", "../550e8400-e29b-41d4-a716-446655440000", False),
        
        # Path normalization cases
        ("Path with redundant slashes", "dir//file.txt", True),
        ("Path with current dir notation", "./file.txt", True),
        ("Path with combined issues", "dir/.//../file.txt", False),
    ]
    
    # Run all test cases and track results
    results = []
    for name, path, expected_valid in test_cases:
        result = run_test_case(name, test_base_dir, path, expected_valid)
        results.append((name, result))
    
    # Print summary
    print("\n\033[1m=== Test Summary ===\033[0m")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed != total:
        print("\nFailed tests:")
        for name, result in results:
            if not result:
                print(f"- {name}")


if __name__ == "__main__":
    print("Running path validation security tests...\n")
    run_test_cases() 