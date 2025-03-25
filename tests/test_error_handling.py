"""
Consolidated test script for error handling in the Insurance Report Generator.
This script automates the testing of error handling functionality across the application.
"""

import sys
import subprocess
import traceback

# Set colors for terminal output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_header(message):
    """Print a formatted header message."""
    print(f"\n{YELLOW}{message}{NC}")
    print("=" * len(message))

def print_success(message):
    """Print a success message."""
    print(f"{GREEN}✓ {message}{NC}")

def print_error(message):
    """Print an error message."""
    print(f"{RED}✗ {message}{NC}")

def print_info(message):
    """Print an informational message."""
    print(f"{BLUE}ℹ {message}{NC}")

def run_test_module(module_name):
    """Run a specific test module and return success status."""
    print_header(f"Running {module_name}")
    
    try:
        # Use Python's subprocess to run the test module
        result = subprocess.run(
            [sys.executable, "-m", module_name],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Print the output
        print(result.stdout)
        
        if result.stderr:
            print_info("Stderr output:")
            print(result.stderr)
        
        print_success(f"{module_name} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"{module_name} failed with exit code {e.returncode}")
        print(e.stdout)
        print(e.stderr)
        return False
    except Exception as e:
        print_error(f"Error running {module_name}: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Main function to run all tests."""
    print_header("Insurance Report Generator - Error Handling Test Suite")
    
    # Track overall success
    all_successful = True
    
    # First, run the error handling tests
    success = run_test_module("backend.tests.test_error_handling")
    all_successful = all_successful and success
    
    # Next, run the chunked upload tests which also test error handling
    success = run_test_module("backend.tests.test_chunked_upload")
    all_successful = all_successful and success
    
    # Print final summary
    print_header("Test Summary")
    if all_successful:
        print_success("All tests completed successfully!")
    else:
        print_error("Some tests failed. See details above.")
    
    # Return exit code based on success
    return 0 if all_successful else 1

if __name__ == "__main__":
    sys.exit(main()) 