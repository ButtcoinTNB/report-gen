#!/usr/bin/env python
"""
Simple test script to verify Python imports are working correctly.
This tests that our fix for the types module conflict works.
"""

import sys
import os

# Add parent directory to path so we can import app_types
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from types import GenericAlias  # This should import from Python's built-in types module
from app_types import APIResponse, SingleAPIResponse  # This should import from our custom app_types module

def main():
    """Simple test function to verify imports."""
    print("Python version:", sys.version)
    print("Successfully imported GenericAlias from built-in types module:", GenericAlias)
    print("Successfully imported from custom app_types module:", APIResponse, SingleAPIResponse)
    print("Import test successful!")

if __name__ == "__main__":
    main() 