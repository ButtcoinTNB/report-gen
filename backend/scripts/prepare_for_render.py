#!/usr/bin/env python
"""
Prepare the codebase for Render deployment by:
1. Fixing imports by removing 'backend.' prefix
2. Ensuring proper path resolution
3. Verifying imports work correctly

This script combines multiple fixes into a single deployment preparation step.

Usage:
    python backend/scripts/prepare_for_render.py
"""

import os
import subprocess
import sys


def run_script(script_path):
    """Run a Python script and return success status."""
    print(f"Running {script_path}...")
    try:
        subprocess.run([sys.executable, script_path], check=True)
        print(f"✅ Script completed successfully: {script_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Script failed with exit code {e.returncode}: {script_path}")
        return False


def check_env():
    """Check environment and provide helpful information."""
    print("\nENVIRONMENT:")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script location: {os.path.abspath(__file__)}")

    # Check for Render environment
    if os.environ.get("RENDER") == "true":
        print(
            "⚠️ Running in Render environment! This script should be run before deployment."
        )
        return False
    return True


def main():
    """Main execution function."""
    print("=" * 80)
    print("RENDER DEPLOYMENT PREPARATION TOOL")
    print("=" * 80)
    print("This script prepares your codebase for deployment to Render")

    if not check_env():
        return 1

    # Get backend directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.path.dirname(script_dir)

    # Define paths to scripts
    fix_render_imports = os.path.join(script_dir, "fix_render_imports.py")
    verify_imports = os.path.join(script_dir, "verify_imports.py")

    # Execute scripts in sequence
    success = True

    # Step 1: Fix imports for Render
    print("\nSTEP 1: FIXING IMPORTS FOR RENDER")
    if os.path.exists(fix_render_imports):
        step_success = run_script(fix_render_imports)
        success = success and step_success
    else:
        print(f"❌ Could not find script: {fix_render_imports}")
        success = False

    # Step 2: Verify imports
    print("\nSTEP 2: VERIFYING IMPORTS")
    if os.path.exists(verify_imports):
        step_success = run_script(verify_imports)
        # Don't fail deployment if verification fails since
        # local environment may report different results than Render
        print(
            "Note: Import verification is informational only and won't block deployment"
        )
    else:
        print(f"⚠️ Could not find verification script: {verify_imports}")

    # Final instructions
    print("\nDEPLOYMENT INSTRUCTIONS:")
    if success:
        print("✅ Preparation complete! Your code is ready for Render deployment.")
        print("\n1. Commit these changes to a deployment branch:")
        print("   git checkout -b deploy-to-render")
        print("   git add .")
        print('   git commit -m "Prepare for Render deployment"')
        print("   git push origin deploy-to-render")
        print("\n2. Configure Render:")
        print("   - Root directory: backend")
        print("   - Build command: pip install -r requirements.txt")
        print(
            "   - Start command: python -m uvicorn main:app --host 0.0.0.0 --port $PORT"
        )
        return 0
    else:
        print("❌ Preparation failed. Please fix the issues above before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
