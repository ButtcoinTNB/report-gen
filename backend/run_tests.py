#!/usr/bin/env python3
"""
Test runner script for the Insurance Report Generator backend
"""
import os
import sys
import pytest
import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_runner")

def run_tests():
    """Run all test suites and generate report"""
    logger.info("Starting test run...")
    start_time = datetime.now()

    # Create test results directory
    results_dir = "test_results"
    os.makedirs(results_dir, exist_ok=True)

    # Generate timestamp for this test run
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(results_dir, f"test_report_{timestamp}.txt")

    # Define test suites to run
    test_suites = [
        "tests/test_api_endpoints.py",
        "tests/test_supabase_rls.py",
        "simple_test.py",
        "test_supabase.py",
        "test_file_processor.py"
    ]

    # Run tests with pytest
    args = [
        "-v",
        "--capture=no",  # Show print statements
        "--log-cli-level=INFO",  # Show logs
        "-s"  # Don't capture stdout
    ]
    args.extend(test_suites)

    # Redirect output to file
    with open(report_file, 'w') as f:
        logger.info("Running test suites...")
        exit_code = pytest.main(args)

    # Calculate duration
    duration = datetime.now() - start_time

    # Log results
    if exit_code == 0:
        logger.info("✅ All tests passed successfully!")
    else:
        logger.error("❌ Some tests failed!")

    logger.info(f"Test run completed in {duration.total_seconds():.2f} seconds")
    logger.info(f"Test report generated: {report_file}")

    return exit_code

def check_environment():
    """Check if environment is properly configured for tests"""
    logger.info("Checking environment configuration...")

    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "UPLOAD_DIR",
        "GENERATED_REPORTS_DIR"
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error("❌ Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        return False

    # Check directories
    required_dirs = [
        "uploads",
        "generated_reports",
        "tests",
        "test_results"
    ]

    for directory in required_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")
            except Exception as e:
                logger.error(f"❌ Failed to create directory {directory}: {e}")
                return False

    logger.info("✅ Environment check passed")
    return True

def cleanup_test_artifacts():
    """Clean up temporary files created during tests"""
    logger.info("Cleaning up test artifacts...")

    cleanup_dirs = [
        "uploads",
        "generated_reports"
    ]

    for directory in cleanup_dirs:
        if os.path.exists(directory):
            try:
                # Only remove files, keep the directory structure
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                logger.info(f"Cleaned up directory: {directory}")
            except Exception as e:
                logger.warning(f"Warning: Failed to clean up {directory}: {e}")

def main():
    """Main entry point"""
    logger.info("=== Insurance Report Generator Test Runner ===")

    # Check environment first
    if not check_environment():
        logger.error("Environment check failed. Please fix the issues and try again.")
        sys.exit(1)

    try:
        # Run the tests
        exit_code = run_tests()

        # Clean up test artifacts
        cleanup_test_artifacts()

        # Exit with the test result code
        sys.exit(exit_code)

    except KeyboardInterrupt:
        logger.info("\nTest run interrupted by user")
        cleanup_test_artifacts()
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error during test execution: {e}")
        cleanup_test_artifacts()
        sys.exit(1)

if __name__ == "__main__":
    main() 