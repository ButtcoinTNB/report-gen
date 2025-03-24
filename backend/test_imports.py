"""
Test script to verify imports are working correctly.
Run this on Render to debug import issues.
"""

print("Starting import test...")

try:
    from models import File, Report, User

    print("✅ Successfully imported from models")
    # Use the imported classes to avoid F401 errors
    dummy_file = File
    dummy_report = Report
    dummy_user = User
except ImportError as e:
    print(f"❌ Failed to import from models: {e}")

try:
    from models import File, Report, User

    print("✅ Successfully imported from models")
    # Use the imported classes to avoid F401 errors
    dummy_file = File
    dummy_report = Report
    dummy_user = User
except ImportError as e:
    print(f"❌ Failed to import from models: {e}")

print("Import test complete.")
