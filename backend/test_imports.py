"""
Test script to verify imports are working correctly.
Run this on Render to debug import issues.
"""

print("Starting import test...")

try:
    from models import File, Report, User

    print("✅ Successfully imported from models")
except ImportError as e:
    print(f"❌ Failed to import from models: {e}")

try:
    from models import File, Report, User

    print("✅ Successfully imported from models")
except ImportError as e:
    print(f"❌ Failed to import from models: {e}")

print("Import test complete.")
