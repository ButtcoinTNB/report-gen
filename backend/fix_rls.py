#!/usr/bin/env python
"""
Script to fix Row Level Security (RLS) policies for the documents table in Supabase.
This allows anonymous access to the documents table for development purposes.
"""

import asyncio
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fix_rls")

try:
    from utils.supabase_helper import create_supabase_client
    from config import settings
except ImportError:
    sys.path.append('.')
    try:
        from backend.utils.supabase_helper import create_supabase_client
        from backend.config import settings
    except ImportError:
        logger.error("Failed to import required modules. Make sure you're running from the project root.")
        sys.exit(1)

async def fix_rls_policies():
    """
    Fix Row Level Security policies for the documents table
    """
    logger.info("Starting RLS policy fix for documents table...")
    
    try:
        # Create a Supabase client
        supabase = await create_supabase_client()
        
        # SQL for creating public access policy
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
        
        # Execute SQL to fix RLS
        logger.info("Executing SQL to fix RLS policies...")
        result = await supabase.rpc('run_sql', {'query': sql}).execute()
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Error applying RLS policy: {result.error}")
            return False
            
        logger.info("Successfully applied public access policy to documents table")
        
        # Test the policy by inserting a test document
        logger.info("Testing the RLS policy with a document insert...")
        test_doc = {
            "filename": "test_rls_fix.pdf",
            "content_type": "application/pdf",
            "size": 1024,
            "status": "uploaded"
        }
        
        test_result = await supabase.table("documents").insert(test_doc).execute()
        
        if hasattr(test_result, 'error') and test_result.error:
            logger.error(f"Policy test failed: {test_result.error}")
            return False
            
        logger.info("Successfully inserted test document - RLS policy is working!")
        
        # Clean up the test document
        if test_result.data and len(test_result.data) > 0 and 'id' in test_result.data[0]:
            await supabase.table('documents').delete().eq('id', test_result.data[0]['id']).execute()
            logger.info("Test document cleaned up")
            
        return True
            
    except Exception as e:
        logger.error(f"Error fixing RLS policies: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info(f"Starting RLS policy fix script with Supabase URL: {settings.SUPABASE_URL}")
    success = asyncio.run(fix_rls_policies())
    
    if success:
        logger.info("✅ RLS policies fixed successfully!")
    else:
        logger.error("❌ Failed to fix RLS policies") 