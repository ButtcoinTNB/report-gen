#!/usr/bin/env python
"""
Pre-Deployment Preparation Script

This script prepares the codebase for production deployment by:
1. Standardizing import patterns across all API modules
2. Verifying that all necessary imports are present
3. Ensuring compatibility with both development and production environments

Usage:
    python -m backend.scripts.prepare_for_production

Options:
    --check-only    Only check for issues without fixing them
    --verbose       Show detailed information during processing
"""

import argparse
import importlib.util
import os
import subprocess
import sys


def is_module_available(module_name):
    """Check if a module is available to import"""
    return importlib.util.find_spec(module_name) is not None


def run_script(script_name, args=None):
    """Run another Python script with the given arguments"""
    if args is None:
        args = []

    # Construct the command
    cmd = [sys.executable, "-m", f"backend.scripts.{script_name}"] + args

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print(f"Errors:\n{result.stderr}")

    return result.returncode == 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Prepare codebase for production deployment"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for issues without fixing them",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed information"
    )

    args = parser.parse_args()

    # Ensure we're running from the project root
    if not os.path.exists("backend/api"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(os.path.join(script_dir, "../.."))

    if not os.path.exists("backend/api"):
        print(
            "Error: Could not find backend/api directory. Please run this script from the project root."
        )
        return 1

    print("=" * 80)
    print("PRE-DEPLOYMENT PREPARATION")
    print("=" * 80)

    # Check if required modules are available
    print("\nChecking for required modules...")
    missing_modules = []
    for module in ["ast", "re"]:
        if not is_module_available(module):
            missing_modules.append(module)

    if missing_modules:
        print(
            f"Error: The following required modules are missing: {', '.join(missing_modules)}"
        )
        print("Please install them using: pip install " + " ".join(missing_modules))
        return 1

    print("All required modules are available.")

    # Step 1: Standardize imports
    print("\n" + "=" * 60)
    print("STEP 1: STANDARDIZING IMPORTS")
    print("=" * 60)

    standardize_args = ["--verbose"] if args.verbose else []
    if args.check_only:
        standardize_args.append("--dry-run")

    success = run_script("standardize_imports", standardize_args)
    if not success:
        print("Error: Import standardization failed.")
        return 1

    # Step 2: Verify imports
    print("\n" + "=" * 60)
    print("STEP 2: VERIFYING IMPORTS")
    print("=" * 60)

    verify_args = ["--verbose"] if args.verbose else []
    if not args.check_only:
        verify_args.append("--fix")

    success = run_script("verify_imports", verify_args)
    if not success:
        print("Error: Import verification failed.")
        print("Please run with the --fix option to automatically fix issues.")
        return 1

    # Step 3: Ensure init files are present
    print("\n" + "=" * 60)
    print("STEP 3: ENSURING __init__.py FILES")
    print("=" * 60)

    # Simple implementation to create missing __init__.py files
    for root, dirs, files in os.walk("backend"):
        if root.startswith(os.path.join("backend", ".")):
            continue  # Skip hidden directories

        init_file = os.path.join(root, "__init__.py")
        if not os.path.exists(init_file):
            if not args.check_only:
                with open(init_file, "w") as f:
                    f.write("# Auto-generated __init__.py file\n")
                print(f"Created {init_file}")
            else:
                print(f"Would create {init_file}")

    # Step 4: Print success message
    print("\n" + "=" * 60)
    print("COMPLETED SUCCESSFULLY!")
    print("=" * 60)

    print("\nThe codebase is now prepared for production deployment.")

    if args.check_only:
        print("\nNote: This was a check-only run. No changes were made.")
        print("Run without --check-only to apply the changes.")
    else:
        print("\nChanges made:")
        print("1. Standardized import patterns with hybrid try/except blocks")
        print("2. Added missing imports to all API modules")
        print("3. Created any missing __init__.py files")
        print("\nReady for deployment!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
