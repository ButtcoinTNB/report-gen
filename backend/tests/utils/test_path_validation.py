#!/usr/bin/env python
"""
Test script for path validation security functions.
Tests various inputs including directory traversal attempts.

Usage:
    pytest backend/tests/utils/test_path_validation.py
"""

import os
import sys
import pytest
from typing import Dict, List, Tuple
from pathlib import Path

# Import the functions we want to test
from backend.utils.storage import validate_path, get_safe_file_path


def test_valid_paths():
    """Test cases with valid paths."""
    test_base_dir = os.path.join(os.getcwd(), "tmp", "path_test")
    os.makedirs(test_base_dir, exist_ok=True)
    
    # Valid test cases
    test_cases = [
        ("Simple valid path", "file.txt"),
        ("Valid path with directory", "dir/file.txt"),
        ("Valid UUID filename", "550e8400-e29b-41d4-a716-446655440000.docx"),
        ("Only dots", "..."),  # This is a valid filename, not traversal
        ("Path with special chars", "file-!@#$%^&*().txt"),
        ("Valid UUID format", "550e8400-e29b-41d4-a716-446655440000"),
        ("Path with redundant slashes", "dir//file.txt"),
        ("Path with current dir notation", "./file.txt"),
    ]
    
    for name, path in test_cases:
        is_valid, validated_path = validate_path(path, test_base_dir)
        assert is_valid, f"Test case failed: {name}"


def test_invalid_paths():
    """Test cases with invalid paths that should be rejected."""
    test_base_dir = os.path.join(os.getcwd(), "tmp", "path_test")
    os.makedirs(test_base_dir, exist_ok=True)
    
    # Invalid test cases
    test_cases = [
        ("Simple traversal", "../file.txt"),
        ("Double traversal", "../../file.txt"),
        ("Nested traversal", "dir/../../../file.txt"),
        ("Absolute path", "/etc/passwd"),
        ("Encoded traversal", "..%2Ffile.txt"),
        ("URL encoded traversal", "%2e%2e%2ffile.txt"),
        ("Null byte injection", "file.txt\0.jpg"),
        ("Empty path", ""),
        ("Invalid UUID format", "not-a-valid-uuid"),
        ("UUID with path traversal", "../550e8400-e29b-41d4-a716-446655440000"),
        ("Path with combined issues", "dir/.//../file.txt"),
    ]
    
    for name, path in test_cases:
        is_valid, validated_path = validate_path(path, test_base_dir)
        assert not is_valid, f"Test case should fail: {name}"


def test_safe_file_path():
    """Test the get_safe_file_path function."""
    test_base_dir = os.path.join(os.getcwd(), "tmp", "path_test")
    os.makedirs(test_base_dir, exist_ok=True)
    
    # Valid paths
    safe_path = get_safe_file_path("file.txt", test_base_dir)
    assert safe_path is not None
    assert test_base_dir in str(safe_path)
    
    # Invalid paths should return None
    unsafe_path = get_safe_file_path("../file.txt", test_base_dir)
    assert unsafe_path is None 