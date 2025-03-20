import os
import sys
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Get Supabase credentials (either from .env or user input)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # This should be the service_role key for admin operations

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Supabase credentials not found in environment variables.")
    SUPABASE_URL = input("Enter your Supabase URL: ")
    SUPABASE_KEY = input("Enter your Supabase service_role key: ")

# SQL to set up the schema_check function
SCHEMA_CHECK_FUNCTION = """
CREATE OR REPLACE FUNCTION schema_check(table_name text)
RETURNS json AS $$
DECLARE
    result json;
BEGIN
    SELECT json_agg(json_build_object(
        'column_name', column_name,
        'data_type', data_type,
        'is_nullable', is_nullable
    ))
    INTO result
    FROM information_schema.columns
    WHERE table_name = $1;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

# SQL to set up the run_sql function
RUN_SQL_FUNCTION = """
CREATE OR REPLACE FUNCTION run_sql(query text)
RETURNS json AS $$
DECLARE
    result json;
BEGIN
    EXECUTE 'WITH query_result AS (' || query || ') SELECT json_agg(row_to_json(query_result)) FROM query_result' INTO result;
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

# SQL to add report_id column and set up triggers
SETUP_REPORT_ID = """
-- Only add the column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'reports' AND column_name = 'report_id'
    ) THEN
        ALTER TABLE reports
        ADD COLUMN report_id UUID NOT NULL DEFAULT gen_random_uuid();
        
        -- Add UNIQUE constraint
        ALTER TABLE reports 
        ADD CONSTRAINT reports_report_id_unique UNIQUE (report_id);
        
        -- Add comment
        COMMENT ON COLUMN reports.report_id IS 'UUID identifier for reports, used as external ID';
    END IF;
END $$;

-- Create the UUID generation function for the trigger
CREATE OR REPLACE FUNCTION set_report_uuid()
RETURNS TRIGGER AS $$
BEGIN
  -- Only set report_id if it's NULL
  IF NEW.report_id IS NULL THEN
    NEW.report_id := gen_random_uuid();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Only create the trigger if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_trigger 
        WHERE tgname = 'ensure_report_has_uuid'
    ) THEN
        CREATE TRIGGER ensure_report_has_uuid
        BEFORE INSERT ON reports
        FOR EACH ROW
        EXECUTE FUNCTION set_report_uuid();
    END IF;
END $$;

-- Create indexes (using IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS reports_id_idx ON reports(id);
CREATE INDEX IF NOT EXISTS reports_report_id_idx ON reports(report_id);
"""

def setup_supabase_functions():
    """Set up necessary Supabase database functions"""
    try:
        # Initialize Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Execute SQL to set up helper functions
        print("Setting up schema_check function...")
        result = supabase.rpc(
            'run_sql',
            {
                'query': SCHEMA_CHECK_FUNCTION
            }
        ).execute()
        print("✅ Schema check function created")
        
        print("Setting up run_sql function...")
        result = supabase.rpc(
            'run_sql',
            {
                'query': RUN_SQL_FUNCTION
            }
        ).execute()
        print("✅ Run SQL function created")
        
        return True
    except Exception as e:
        print(f"Error setting up Supabase helper functions: {str(e)}")
        return False

def setup_report_id():
    """Set up report_id column and related constraints/triggers"""
    try:
        # Initialize Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Execute SQL to set up report_id
        print("Setting up report_id column and related objects...")
        result = supabase.rpc(
            'run_sql',
            {
                'query': SETUP_REPORT_ID
            }
        ).execute()
        print("✅ report_id column and related objects created")
        
        return True
    except Exception as e:
        print(f"Error setting up report_id: {str(e)}")
        return False

if __name__ == "__main__":
    print("Setting up Supabase helper functions and report_id column...")
    
    # First try to set up the helper functions
    if setup_supabase_functions():
        # Then set up the report_id column
        if setup_report_id():
            print("\n✅ All setup completed successfully!")
            print("\nNow run check_supabase.py to verify the setup.")
        else:
            print("\n❌ Failed to set up report_id column.")
    else:
        print("\n❌ Failed to set up helper functions.")
        print("This might be due to insufficient permissions. Make sure you're using the service_role key.") 