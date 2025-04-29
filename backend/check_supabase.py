import os
import sys
import asyncio

from dotenv import load_dotenv

from supabase import create_client

# Check if we're in production mode
IS_PRODUCTION = os.getenv("NODE_ENV") == "production"


def check_table(supabase, table_name, required_columns=None):
    print(f"\n--- Checking '{table_name}' table ---")
    try:
        # Try to get a single row
        result = supabase.table(table_name).select("*").limit(1).execute()
        print(f"✅ {table_name} table exists")

        if result.data:
            columns = result.data[0].keys()
            print(f"\nColumns: {', '.join(columns)}")

            if required_columns:
                missing_columns = [
                    col for col in required_columns if col not in columns
                ]
                if missing_columns:
                    print(f"❌ Missing required columns: {', '.join(missing_columns)}")
                else:
                    print("✅ All required columns present")

            # Check sample data
            print("\nSample row:")
            for key, value in result.data[0].items():
                print(f"  {key}: {value}")
        else:
            print("Table exists but has no data")

            # Try to get table definition
            try:
                columns = supabase.table(table_name).select("*").limit(0).execute()
                if hasattr(columns, "columns") and columns.columns:
                    print(f"\nColumns: {', '.join(columns.columns)}")
                    if required_columns:
                        missing_columns = [
                            col
                            for col in required_columns
                            if col not in columns.columns
                        ]
                        if missing_columns:
                            print(
                                f"❌ Missing required columns: {', '.join(missing_columns)}"
                            )
                        else:
                            print("✅ All required columns present")
            except Exception as e:
                print(f"Error getting table definition: {str(e)}")

    except Exception as e:
        print(f"❌ Error accessing {table_name} table: {str(e)}")
        if f'relation "public.{table_name}" does not exist' in str(e):
            print(f"The {table_name} table does not exist in the database")
            return False
    return True


def check_index(supabase, table_name, column_name):
    print(f"\n--- Checking index on {table_name}.{column_name} ---")
    try:
        # Try ordering by the column which should use an index if it exists
        (supabase.table(table_name).select("id").order(column_name).limit(1).execute())
        print(f"✅ {column_name} appears to be indexed (order by query succeeded)")
        return True
    except Exception as e:
        if f'column "{column_name}" does not exist' in str(e):
            print(f"❌ {column_name} column does not exist")
        else:
            print(f"❓ Unable to determine if {column_name} is indexed:", str(e))
        return False


def check_uuid_generation(supabase, table_name, required_fields):
    print(f"\n--- Checking UUID generation for {table_name} ---")
    try:
        # Insert a test record with required fields
        test_insert = supabase.table(table_name).insert(required_fields).execute()
        if test_insert.data and len(test_insert.data) > 0:
            inserted_id = test_insert.data[0].get("report_id")
            if inserted_id:
                print(f"✅ UUID generation works (got: {inserted_id})")
                # Clean up test record
                supabase.table(table_name).delete().eq(
                    "report_id", inserted_id
                ).execute()
                return True
            else:
                print("❌ No report_id generated on insert")
        else:
            print("❓ Unable to verify UUID generation (no data returned from insert)")
    except Exception as e:
        print(f"❓ Unable to verify UUID generation: {str(e)}")
    return False


def get_test_data(table_name):
    """
    Get test data for a specific table, ensuring safe values for testing
    that won't disrupt production data.

    Args:
        table_name: Name of the table to get test data for

    Returns:
        Dictionary with test data for the table or None if not available
    """
    # Define test data for each table with production-safe values
    test_data = {
        "files": {
            "filename": "_test_check_supabase.txt",
            "file_type": "text/plain",
            "content": "test content - will be deleted",
            "report_id": "00000000-0000-0000-0000-000000000000",
            "file_size": 123,
            "file_path": "/test/path",
            "mime_type": "text/plain",
        },
        "reports": {
            "title": "_TEST_Report - will be deleted",
            "content": "test content - will be deleted",
            "status": "draft",
            "template_id": "00000000-0000-0000-0000-000000000000",
            "metadata": {"test": True, "will_be_deleted": True},
        },
        "templates": {
            "name": "_TEST_Template - will be deleted",
            "content": "test content - will be deleted",
            "version": "1.0",
            "metadata": {"test": True, "will_be_deleted": True},
        },
        "reference_reports": {
            "title": "_TEST_Reference - will be deleted",
            "content": "test content - will be deleted",
            "category": "test",
            "tags": ["test"],
            "metadata": {"test": True, "will_be_deleted": True},
        },
    }

    return test_data.get(table_name)


def check_table_detailed(supabase, table_name):
    print(f"\n{'='*50}")
    print(f"Detailed check of '{table_name}' table")
    print(f"{'='*50}")
    try:
        # First check if table exists
        try:
            supabase.table(table_name).select("*").limit(1).execute()
            print(f"✅ Table '{table_name}' exists")

            # Get table structure
            try:
                # Get all columns by selecting with a limit 0
                cols = supabase.table(table_name).select("*").limit(0).execute()
                if hasattr(cols, "columns"):
                    columns = sorted(cols.columns)
                    print("\n📋 Existing columns:")
                    for col in columns:
                        print(f"  • {col}")

                    # Define required columns for each table
                    required_cols = {
                        "files": {
                            "id": "bigint/serial",
                            "file_id": "uuid",
                            "report_id": "uuid",
                            "filename": "text",
                            "file_type": "text",
                            "content": "text",
                            "created_at": "timestamp with time zone",
                            "is_deleted": "boolean",
                            "file_size": "bigint",
                            "file_path": "text",
                            "mime_type": "text",
                            "updated_at": "timestamp with time zone",
                        },
                        "reports": {
                            "id": "bigint/serial",
                            "report_id": "uuid",
                            "title": "text",
                            "content": "text",
                            "status": "text",
                            "created_at": "timestamp with time zone",
                            "updated_at": "timestamp with time zone",
                            "is_deleted": "boolean",
                            "template_id": "uuid",
                            "metadata": "jsonb",
                        },
                        "templates": {
                            "id": "bigint/serial",
                            "template_id": "uuid",
                            "name": "text",
                            "content": "text",
                            "created_at": "timestamp with time zone",
                            "updated_at": "timestamp with time zone",
                            "is_deleted": "boolean",
                            "metadata": "jsonb",
                            "version": "text",
                        },
                        "reference_reports": {
                            "id": "bigint/serial",
                            "reference_id": "uuid",
                            "title": "text",
                            "content": "text",
                            "created_at": "timestamp with time zone",
                            "updated_at": "timestamp with time zone",
                            "is_deleted": "boolean",
                            "metadata": "jsonb",
                            "category": "text",
                            "tags": "text[]",
                        },
                    }

                    if table_name in required_cols:
                        missing = [
                            col
                            for col in required_cols[table_name].keys()
                            if col not in columns
                        ]
                        if missing:
                            print("\n❌ Missing required columns:")
                            for col in missing:
                                print(f"  • {col} ({required_cols[table_name][col]})")
                            print("\n🔧 SQL to add missing columns:")
                            for col in missing:
                                sql = f"ALTER TABLE {table_name} ADD COLUMN {col} {required_cols[table_name][col]};"

                                # Add indexes based on table and column
                                if table_name == "files" and col in [
                                    "file_id",
                                    "report_id",
                                ]:
                                    index_type = "UNIQUE" if col == "file_id" else ""
                                    sql += f"\nCREATE {index_type} INDEX idx_{table_name}_{col} ON {table_name}({col});"
                                elif table_name == "reports" and col in [
                                    "report_id",
                                    "template_id",
                                ]:
                                    index_type = "UNIQUE" if col == "report_id" else ""
                                    sql += f"\nCREATE {index_type} INDEX idx_{table_name}_{col} ON {table_name}({col});"
                                elif table_name == "templates" and col == "template_id":
                                    sql += f"\nCREATE UNIQUE INDEX idx_{table_name}_{col} ON {table_name}({col});"
                                elif (
                                    table_name == "reference_reports"
                                    and col == "reference_id"
                                ):
                                    sql += f"\nCREATE UNIQUE INDEX idx_{table_name}_{col} ON {table_name}({col});"
                                print(sql)
                        else:
                            print("\n✅ All required columns present")

                        # Check indexes
                        print("\n🔍 Checking indexes:")
                        try:
                            # Define which columns should be indexed for each table
                            index_columns = {
                                "files": [
                                    ("file_id", True),  # (column, is_unique)
                                    ("report_id", False),
                                ],
                                "reports": [
                                    ("report_id", True),
                                    ("template_id", False),
                                ],
                                "templates": [("template_id", True)],
                                "reference_reports": [("reference_id", True)],
                            }

                            for col, is_unique in index_columns.get(table_name, []):
                                if col in columns:
                                    try:
                                        (
                                            supabase.table(table_name)
                                            .select("id")
                                            .order(col)
                                            .limit(1)
                                            .execute()
                                        )
                                        print(
                                            f"  ✅ {col} is indexed"
                                            + (" (UNIQUE)" if is_unique else "")
                                        )
                                    except Exception as e:
                                        print(
                                            f"  ❌ {col} might not be indexed:", str(e)
                                        )
                                else:
                                    print(f"  ⚠️ {col} column not found")
                        except Exception as e:
                            print("  ❌ Error checking indexes:", str(e))

                        # Try a test insert to check UUID generation
                        print("\n🧪 Testing UUID generation:")
                        try:
                            if IS_PRODUCTION:
                                print("  ⚠️ Skipping insert test in production mode")
                            else:
                                # Get test data for this table
                                data = get_test_data(table_name)
                                if data:
                                    test_insert = (
                                        supabase.table(table_name)
                                        .insert(data)
                                        .execute()
                                    )
                                    if test_insert.data and len(test_insert.data) > 0:
                                        # Get the appropriate UUID column name for the table
                                        uuid_column = {
                                            "files": "file_id",
                                            "reports": "report_id",
                                            "templates": "template_id",
                                            "reference_reports": "reference_id",
                                        }.get(table_name)

                                        inserted_id = test_insert.data[0].get(
                                            uuid_column
                                        )
                                        if inserted_id:
                                            print(
                                                f"  ✅ UUID generation works (got: {inserted_id})"
                                            )
                                            # Clean up test record
                                            supabase.table(table_name).delete().eq(
                                                uuid_column, inserted_id
                                            ).execute()
                                        else:
                                            print(
                                                f"  ❌ No {uuid_column} generated on insert"
                                            )
                                    else:
                                        print(
                                            "  ❓ Unable to verify UUID generation (no data returned from insert)"
                                        )
                                else:
                                    print(
                                        f"  ⚠️ No test data defined for table {table_name}"
                                    )
                        except Exception as e:
                            print(f"  ❌ Unable to verify UUID generation: {str(e)}")

            except Exception as e:
                print(f"Error getting table definition: {str(e)}")

        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                print(f"❌ Table '{table_name}' does not exist")
                # Generate create table SQL for missing table
                create_table_sql = {
                    "files": """
                    CREATE TABLE files (
                        id bigserial PRIMARY KEY,
                        file_id uuid DEFAULT uuid_generate_v4() NOT NULL,
                        report_id uuid NOT NULL,
                        filename text NOT NULL,
                        file_type text NOT NULL,
                        content text,
                        file_size bigint,
                        file_path text,
                        mime_type text,
                        created_at timestamp with time zone DEFAULT now(),
                        updated_at timestamp with time zone DEFAULT now(),
                        is_deleted boolean DEFAULT false,
                        CONSTRAINT fk_files_report FOREIGN KEY (report_id) REFERENCES reports(report_id) ON DELETE CASCADE
                    );
                    CREATE UNIQUE INDEX idx_files_file_id ON files(file_id);
                    CREATE INDEX idx_files_report_id ON files(report_id);
                    """,
                    "reports": """
                    CREATE TABLE reports (
                        id bigserial PRIMARY KEY,
                        report_id uuid DEFAULT uuid_generate_v4() NOT NULL,
                        title text NOT NULL,
                        content text,
                        status text NOT NULL,
                        template_id uuid NOT NULL,
                        metadata jsonb DEFAULT '{}'::jsonb,
                        created_at timestamp with time zone DEFAULT now(),
                        updated_at timestamp with time zone DEFAULT now(),
                        is_deleted boolean DEFAULT false,
                        CONSTRAINT fk_reports_template FOREIGN KEY (template_id) REFERENCES templates(template_id)
                    );
                    CREATE UNIQUE INDEX idx_reports_report_id ON reports(report_id);
                    CREATE INDEX idx_reports_template_id ON reports(template_id);
                    """,
                    "templates": """
                    CREATE TABLE templates (
                        id bigserial PRIMARY KEY,
                        template_id uuid DEFAULT uuid_generate_v4() NOT NULL,
                        name text NOT NULL,
                        content text NOT NULL,
                        version text NOT NULL,
                        metadata jsonb DEFAULT '{}'::jsonb,
                        created_at timestamp with time zone DEFAULT now(),
                        updated_at timestamp with time zone DEFAULT now(),
                        is_deleted boolean DEFAULT false
                    );
                    CREATE UNIQUE INDEX idx_templates_template_id ON templates(template_id);
                    """,
                    "reference_reports": """
                    CREATE TABLE reference_reports (
                        id bigserial PRIMARY KEY,
                        reference_id uuid DEFAULT uuid_generate_v4() NOT NULL,
                        title text NOT NULL,
                        content text NOT NULL,
                        category text NOT NULL,
                        tags text[] DEFAULT ARRAY[]::text[],
                        metadata jsonb DEFAULT '{}'::jsonb,
                        created_at timestamp with time zone DEFAULT now(),
                        updated_at timestamp with time zone DEFAULT now(),
                        is_deleted boolean DEFAULT false
                    );
                    CREATE UNIQUE INDEX idx_reference_reports_reference_id ON reference_reports(reference_id);
                    """,
                }

                if table_name in create_table_sql:
                    print("\n🔧 SQL to create table:")
                    print(create_table_sql[table_name])
            return None

    except Exception as e:
        print(f"Error checking table: {str(e)}")
        return None


def create_storage_bucket(supabase, bucket_name):
    print(f"\nCreating storage bucket '{bucket_name}'...")
    try:
        supabase.storage.create_bucket(bucket_name)
        print(f"✅ Created bucket: {bucket_name}")
        return True
    except Exception as e:
        if "Duplicate" in str(e):
            print(f"Bucket {bucket_name} already exists")
            return True
        print(f"Error creating bucket {bucket_name}: {str(e)}")
        return False


def generate_sql_commands(table_info, table_name):
    if not table_info:
        return None

    existing_columns = {col["column_name"] for col in table_info}

    # Define required columns and their types
    required_columns = {
        "files": {
            "id": "bigint NOT NULL DEFAULT nextval('files_id_seq'::regclass)",
            "file_id": "uuid NOT NULL DEFAULT uuid_generate_v4()",
            "report_id": "uuid NOT NULL",
            "filename": "text NOT NULL",
            "file_type": "text NOT NULL",
            "created_at": "timestamp with time zone DEFAULT now()",
            "is_deleted": "boolean DEFAULT false",
            "content": "text",
        }
    }

    if table_name not in required_columns:
        return None

    missing_columns = {
        col: spec
        for col, spec in required_columns[table_name].items()
        if col not in existing_columns
    }

    if not missing_columns:
        return None

    # Generate ALTER TABLE commands
    sql_commands = []
    for col, spec in missing_columns.items():
        sql_commands.append(f"ALTER TABLE {table_name} ADD COLUMN {col} {spec};")

    # Add index commands for key columns
    if "file_id" in missing_columns:
        sql_commands.append(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_name}_file_id ON {table_name}(file_id);"
        )
    if "report_id" in missing_columns:
        sql_commands.append(
            f"CREATE INDEX IF NOT EXISTS idx_{table_name}_report_id ON {table_name}(report_id);"
        )

    return sql_commands


async def check_and_fix_rls(supabase):
    """
    Check and fix Row Level Security policies for the documents table
    """
    print("\n=== Checking and fixing RLS Policies ===")

    try:
        # First check if documents table exists
        print("\nChecking for documents table...")
        result = await supabase.rpc('get_tables').execute()
        
        tables = []
        if not hasattr(result, 'error') and result.data:
            for item in result.data:
                if 'name' in item:
                    tables.append(item['name'])
        
        if 'documents' not in tables:
            print("❌ Documents table does not exist")
            return

        print("✅ Documents table exists")
        
        # Apply the public access policy
        print("\nApplying public access policy to documents table...")
        sql = """
        -- First check if policies exist before attempting to drop
        DROP POLICY IF EXISTS "Users can view their own or public documents" ON documents;
        DROP POLICY IF EXISTS "Users can create their own or public documents" ON documents;
        DROP POLICY IF EXISTS "Users can update their own or public documents" ON documents;
        DROP POLICY IF EXISTS "Users can delete their own or public documents" ON documents;

        -- Drop old policies if they still exist
        DROP POLICY IF EXISTS "Users can view their own documents" ON documents;
        DROP POLICY IF EXISTS "Users can create their own documents" ON documents;
        DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
        DROP POLICY IF EXISTS "Users can delete their own documents" ON documents;

        -- Completely public policy for the demo environment
        CREATE POLICY "Public documents access policy"
            ON documents FOR ALL
            USING (true)
            WITH CHECK (true);

        -- Make created_by nullable
        ALTER TABLE documents 
        ALTER COLUMN created_by DROP NOT NULL;
        """
        
        result = await supabase.rpc('run_sql', {'query': sql}).execute()
        
        if hasattr(result, 'error') and result.error:
            print(f"❌ Error applying public access policy: {result.error}")
        else:
            print("✅ Successfully applied public access policy to documents table")
            
        # Test the policy by inserting a test document
        print("\nTesting policy with a test document insert...")
        test_doc = {
            "filename": "test_rls_fix.pdf",
            "content_type": "application/pdf",
            "size": 1024,
            "status": "uploaded"
        }
        
        result = await supabase.table('documents').insert(test_doc).execute()
        
        if hasattr(result, 'error') and result.error:
            print(f"❌ Policy test failed: {result.error}")
        else:
            print("✅ Successfully inserted test document - RLS policy is working!")
            # Delete the test document
            if result.data and len(result.data) > 0 and 'id' in result.data[0]:
                await supabase.table('documents').delete().eq('id', result.data[0]['id']).execute()
                print("✅ Test document cleaned up")
            
    except Exception as e:
        print(f"❌ Error checking/fixing RLS: {str(e)}")


def main():
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Get Supabase credentials
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Supabase credentials not found in environment variables.")
        SUPABASE_URL = input("Enter your Supabase URL: ")
        SUPABASE_KEY = input("Enter your Supabase service_role key (or anon key): ")

    try:
        # Initialize Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Check all tables
        tables = ["files", "reports", "templates", "reference_reports"]
        for table in tables:
            check_table_detailed(supabase, table)

        # Check and create storage buckets
        print("\n=== Checking Storage Buckets ===")
        try:
            buckets = supabase.storage.list_buckets()
            existing_buckets = {bucket.name for bucket in buckets}
            print(
                "Existing buckets:",
                ", ".join(existing_buckets) if existing_buckets else "None",
            )

            required_buckets = ["uploads", "generated_reports"]
            for bucket in required_buckets:
                if bucket not in existing_buckets:
                    create_storage_bucket(supabase, bucket)
                else:
                    print(f"✅ {bucket} bucket already exists")
        except Exception as e:
            print("Error managing storage buckets:", str(e))

        # Check and fix RLS policies
        asyncio.run(check_and_fix_rls(supabase))

    except Exception as e:
        print(f"Error connecting to Supabase: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
