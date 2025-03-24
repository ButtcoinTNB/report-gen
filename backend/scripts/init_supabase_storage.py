"""
Initialize Supabase storage buckets for the insurance report generator.

This script creates the necessary storage buckets in Supabase:
1. templates - For template files
2. reports - For all report files (reference and generated)
"""

import os
import sys

from dotenv import load_dotenv

# Add parent directory to path to import from project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import Client, create_client

# Load environment variables
load_dotenv()

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    sys.exit(1)


def create_bucket_if_not_exists(
    supabase: Client, bucket_name: str, public: bool = False
):
    """Create a storage bucket if it doesn't already exist."""
    try:
        # Check if bucket exists first
        buckets = supabase.storage.list_buckets()
        bucket_exists = any(bucket.name == bucket_name for bucket in buckets)

        if not bucket_exists:
            print(f"Creating storage bucket: {bucket_name}")
            supabase.storage.create_bucket(bucket_name, options={"public": public})
            print(f"✅ Successfully created bucket: {bucket_name}")
        else:
            print(f"✅ Bucket already exists: {bucket_name}")

    except Exception as e:
        print(f"❌ Error creating bucket {bucket_name}: {str(e)}")


def main():
    print("Initializing Supabase storage buckets for insurance report generator...")

    try:
        # Initialize Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Connected to Supabase successfully")

        # Create storage buckets
        create_bucket_if_not_exists(supabase, "templates")
        create_bucket_if_not_exists(supabase, "reports")

        print("\nStorage initialization complete.")

    except Exception as e:
        print(f"Error initializing Supabase storage: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
