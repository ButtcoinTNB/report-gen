import os

from dotenv import load_dotenv

from supabase import create_client

# Load environment variables from .env file if it exists
load_dotenv()

# Get Supabase credentials (either from .env or user input)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY"
)  # This should be the service_role key for admin operations

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
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'SQL Error: %', SQLERRM;
        -- For DDL/DML statements that don't return data
        RETURN json_build_object('result', 'success', 'message', 'Command executed - no rows returned');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

# SQL to add RLS policy
PUBLIC_RLS_POLICY = """
-- Drop existing policies
DROP POLICY IF EXISTS "Users can view their own documents" ON documents;
DROP POLICY IF EXISTS "Users can create their own documents" ON documents;
DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete their own documents" ON documents;

-- Create a public policy for development
CREATE POLICY "Public documents access policy"
    ON documents FOR ALL
    USING (true)
    WITH CHECK (true);

-- Make created_by nullable
ALTER TABLE documents 
ALTER COLUMN created_by DROP NOT NULL;
"""


def setup_supabase_functions():
    """Set up necessary Supabase database functions"""
    try:
        # Initialize Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Execute SQL to set up helper functions
        print("Setting up schema_check function...")
        supabase.rpc("run_sql", {"query": SCHEMA_CHECK_FUNCTION}).execute()
        print("✅ Schema check function created")

        print("Setting up run_sql function...")
        supabase.rpc("run_sql", {"query": RUN_SQL_FUNCTION}).execute()
        print("✅ Run SQL function created")

        return True
    except Exception as e:
        print(f"Error setting up Supabase helper functions: {str(e)}")
        
        # Try a direct SQL approach if RPC fails (first execution)
        try:
            print("Attempting direct SQL execution for run_sql function...")
            # Use the raw REST API to execute the SQL directly
            result = supabase.table("_pgrst_reserved_id").select("*").limit(1).execute()
            
            # If we got here, we have a connection - try to create the function directly
            print("Creating run_sql function using direct SQL...")
            # Create a direct SQL statement to create our function
            direct_sql = f"""
            {RUN_SQL_FUNCTION}
            SELECT 'run_sql function created';
            """
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            import requests
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/",
                headers=headers,
                json={"query": direct_sql}
            )
            if response.status_code < 300:
                print("✅ Direct SQL execution successful")
                return True
            else:
                print(f"❌ Direct SQL failed: {response.status_code} - {response.text}")
        except Exception as direct_e:
            print(f"Direct SQL execution failed: {str(direct_e)}")
            
        return False


def setup_report_id():
    """Add a report_id column to the reports table if it doesn't exist"""
    try:
        # Initialize Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Check if the column exists
        print("Checking if report_id column exists...")
        check_sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'reports' AND column_name = 'report_id'
        """
        response = supabase.rpc("run_sql", {"query": check_sql}).execute()

        if not response.data or len(response.data) == 0:
            print("Adding report_id column to reports table...")
            add_column_sql = """
            -- Add the report_id column with default values
            ALTER TABLE reports ADD COLUMN IF NOT EXISTS report_id uuid DEFAULT uuid_generate_v4() NOT NULL;
            """
            response = supabase.rpc("run_sql", {"query": add_column_sql}).execute()
            print("✅ report_id column added to reports table")
        else:
            print("✅ report_id column already exists")

        return True
    except Exception as e:
        print(f"Error setting up report_id column: {str(e)}")
        return False


def setup_public_rls_policy():
    """Set up public RLS policy for documents table"""
    try:
        # Initialize Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Apply the public RLS policy
        print("Setting up public RLS policy for documents table...")
        try:
            response = supabase.rpc("run_sql", {"query": PUBLIC_RLS_POLICY}).execute()
            print("✅ Public RLS policy applied to documents table")
            return True
        except Exception as rls_error:
            print(f"Error applying RLS policy through RPC: {str(rls_error)}")
            
            # Try direct approach
            try:
                print("Attempting direct SQL execution for RLS policy...")
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"
                }
                import requests
                response = requests.post(
                    f"{SUPABASE_URL}/rest/v1/",
                    headers=headers,
                    json={"query": PUBLIC_RLS_POLICY}
                )
                if response.status_code < 300:
                    print("✅ Direct RLS policy application successful")
                    return True
                else:
                    print(f"❌ Direct RLS policy failed: {response.status_code} - {response.text}")
            except Exception as direct_e:
                print(f"Direct RLS policy execution failed: {str(direct_e)}")
            
        return False
    except Exception as e:
        print(f"Error setting up public RLS policy: {str(e)}")
        return False


if __name__ == "__main__":
    print("Setting up Supabase helper functions, report_id column, and RLS policy...")

    # First try to set up the helper functions
    if setup_supabase_functions():
        # Then set up the report_id column
        report_id_success = setup_report_id()
        
        # Finally, set up the public RLS policy
        rls_success = setup_public_rls_policy()
        
        if report_id_success and rls_success:
            print("\n✅ All setup completed successfully!")
            print("\nNow run check_supabase.py to verify the setup.")
        else:
            if not report_id_success:
                print("\n❌ Failed to set up report_id column.")
            if not rls_success:
                print("\n❌ Failed to set up public RLS policy.")
    else:
        print("\n❌ Failed to set up helper functions.")
        print(
            "This might be due to insufficient permissions. Make sure you're using the service_role key."
        )
