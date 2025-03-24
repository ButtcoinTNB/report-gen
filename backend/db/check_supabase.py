import os
import sys

from dotenv import load_dotenv

from supabase import create_client

# Load environment variables from .env file if it exists
load_dotenv()

# Get Supabase credentials (either from .env or user input)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Supabase credentials not found in environment variables.")
    SUPABASE_URL = input("Enter your Supabase URL: ")
    SUPABASE_KEY = input("Enter your Supabase service_role key (or anon key): ")

try:
    # Initialize Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Check if the reports table exists and get its structure
    print("\n--- Checking 'reports' table structure ---")

    # Try to describe the table structure directly
    try:
        # This query requires elevated permissions (service_role key)
        query = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'reports'
        """
        columns = (
            supabase.table("information_schema.columns")
            .select("column_name,data_type,is_nullable")
            .eq("table_name", "reports")
            .execute()
        )

        if columns.data:
            print("\nTable structure from information_schema:")
            for col in columns.data:
                print(
                    f"- {col['column_name']} ({col['data_type']}) {'NULL' if col['is_nullable']=='YES' else 'NOT NULL'}"
                )

            # Check for report_id
            report_id_col = next(
                (col for col in columns.data if col["column_name"] == "report_id"), None
            )
            if report_id_col:
                print(
                    "\n✅ report_id column exists with type:",
                    report_id_col["data_type"],
                )
            else:
                print("\n❌ report_id column is MISSING!")
        else:
            print("No columns found in the reports table.")
    except Exception as e:
        print("Error querying information_schema:", str(e))

    # Check for indexes on the reports table
    print("\n--- Checking indexes on 'reports' table ---")
    try:
        # This requires elevated permissions (service_role key)
        indexes_query = """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'reports'
        """
        indexes = (
            supabase.table("pg_indexes")
            .select("indexname,indexdef")
            .eq("tablename", "reports")
            .execute()
        )

        if indexes.data:
            print("Indexes on reports table:")
            for idx in indexes.data:
                print(f"- {idx['indexname']}: {idx['indexdef']}")

            # Check specifically for report_id index
            report_id_index = any(
                "report_id" in idx.get("indexdef", "") for idx in indexes.data
            )
            if report_id_index:
                print("\n✅ report_id is indexed.")
            else:
                print("\n❌ No index found for report_id!")
        else:
            print("No indexes found or insufficient permissions to check indexes.")
    except Exception as e:
        print("Error checking indexes:", str(e))

    # Check for triggers on the reports table
    print("\n--- Checking triggers on 'reports' table ---")
    try:
        triggers_query = """
        SELECT trigger_name, event_manipulation, action_statement
        FROM information_schema.triggers
        WHERE event_object_table = 'reports'
        """
        triggers = (
            supabase.table("information_schema.triggers")
            .select("trigger_name,event_manipulation,action_statement")
            .eq("event_object_table", "reports")
            .execute()
        )

        if triggers.data:
            print("Triggers on reports table:")
            for trg in triggers.data:
                print(
                    f"- {trg['trigger_name']} ({trg['event_manipulation']}): {trg['action_statement']}"
                )

            # Check specifically for UUID generation trigger
            uuid_trigger = any("uuid" in str(trg).lower() for trg in triggers.data)
            if uuid_trigger:
                print("\n✅ UUID generation trigger exists.")
            else:
                print("\n❌ No trigger found for UUID generation!")
        else:
            print("No triggers found or insufficient permissions to check triggers.")
    except Exception as e:
        print("Error checking triggers:", str(e))

except Exception as e:
    print(f"Error connecting to Supabase: {str(e)}")
    sys.exit(1)
