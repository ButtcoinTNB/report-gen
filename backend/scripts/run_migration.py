"""
Script to run SQL migrations through the Supabase client.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials. Please check your .env file.")

def run_migration(migration_file: str):
    """Run a SQL migration file through the Supabase client."""
    print(f"Running migration: {migration_file}")
    
    # Initialize Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Read the migration file
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    # Execute the SQL through the run_sql RPC function
    try:
        result = supabase.rpc('run_sql', {'query': sql}).execute()
        print("Migration completed successfully")
        return result
    except Exception as e:
        print(f"Error running migration: {str(e)}")
        raise

if __name__ == "__main__":
    # Get the migration file path
    migration_file = Path(__file__).parent.parent / "migrations" / "add_document_ids.sql"
    
    # Run the migration
    run_migration(str(migration_file)) 