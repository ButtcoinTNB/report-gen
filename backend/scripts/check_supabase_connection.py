#!/usr/bin/env python
"""
Utility script to check Supabase connection before uploading reference reports.
This script validates that the Supabase credentials are correctly configured.
"""

import os
import sys

import requests

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


def check_supabase_connection():
    """Check if Supabase connection is working."""
    print("\n=== Checking Supabase Connection ===\n")

    # Check if credentials are set
    if not settings.SUPABASE_URL:
        print("❌ SUPABASE_URL is not set in your .env file")
        return False

    if not settings.SUPABASE_KEY:
        print("❌ SUPABASE_KEY is not set in your .env file")
        return False

    print(f"✅ Supabase URL: {settings.SUPABASE_URL}")
    print(
        f"✅ Supabase Key: {settings.SUPABASE_KEY[:5]}...{settings.SUPABASE_KEY[-5:] if len(settings.SUPABASE_KEY) > 10 else ''}"
    )

    # Try to connect to Supabase
    try:
        # Fetch the list of tables (this will fail if credentials are wrong)
        headers = {
            "apikey": settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        }

        print("\nAttempting to connect to Supabase...")

        # Try to list reference_reports table
        response = requests.get(
            f"{settings.SUPABASE_URL}/rest/v1/reference_reports?select=id&limit=1",
            headers=headers,
        )

        if response.status_code == 200:
            print("✅ Successfully connected to Supabase!")
            data = response.json()
            print(f"  - Found reference_reports table with {len(data)} entries")
            return True
        else:
            print(f"❌ Error connecting to Supabase: Status {response.status_code}")
            print(f"  Response: {response.text}")

            # Check if table doesn't exist
            if response.status_code == 404:
                print("\n⚠️ The reference_reports table might not exist.")
                print(
                    "You may need to create it first. Try running the init_supabase.py script."
                )

            return False
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {str(e)}")
        return False


if __name__ == "__main__":
    success = check_supabase_connection()

    if success:
        print("\n✅ Supabase connection is working correctly.")
        print(
            "You can now run upload-reference-reports.py to upload your PDF templates."
        )
    else:
        print("\n❌ Supabase connection failed.")
        print("Please check your credentials in the .env file and try again.")
        print(
            "Make sure you've created a reference_reports table in your Supabase database."
        )
