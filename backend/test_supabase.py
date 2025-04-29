"""
Test script to check Supabase documents table and RLS policies
"""
import asyncio
import json
import sys
from typing import Any, Dict, List

# Add imports with fallback for better compatibility
try:
    from utils.supabase_helper import create_supabase_client, async_supabase_client_context
    from config import settings
except ImportError:
    sys.path.append('.')
    from backend.utils.supabase_helper import create_supabase_client, async_supabase_client_context
    from backend.config import settings

async def test_documents_table() -> None:
    """
    Test querying the documents table and check RLS policies
    """
    print("Testing Supabase documents table...")
    
    try:
        # Create a Supabase client
        async with async_supabase_client_context() as supabase:
            # Test 1: Try to get all documents
            print("\nTest 1: Fetching documents with default client")
            try:
                result = await supabase.table('documents').select('*').limit(5).execute()
                if hasattr(result, 'error') and result.error:
                    print(f"Error: {result.error}")
                else:
                    print(f"Success! Found {len(result.data)} documents:")
                    print(json.dumps(result.data, indent=2))
            except Exception as e:
                print(f"Error fetching documents: {str(e)}")
            
            # Test 2: Insert an anonymous document
            print("\nTest 2: Inserting document without created_by")
            try:
                file_info = {
                    "filename": "test_anonymous.pdf",
                    "content_type": "application/pdf",
                    "size": 1024,
                    "status": "uploaded",
                    "quality_score": 0,
                    "edit_count": 0,
                    "iterations": 0,
                    "time_saved": 0,
                    "download_count": 0,
                    "pages": 1
                }
                
                result = await supabase.table("documents").insert(file_info).execute()
                if hasattr(result, 'error') and result.error:
                    print(f"Error: {result.error}")
                else:
                    print("Success! Document inserted:")
                    print(json.dumps(result.data, indent=2))
            except Exception as e:
                print(f"Error inserting document: {str(e)}")
        
        # Print Supabase configuration
        print("\nSupabase Configuration:")
        print(f"URL: {settings.SUPABASE_URL}")
        print(f"Key: {settings.SUPABASE_KEY[:5]}...{settings.SUPABASE_KEY[-5:] if len(settings.SUPABASE_KEY) > 10 else ''}") 
        
    except Exception as e:
        print(f"Error connecting to Supabase: {str(e)}")

if __name__ == "__main__":
    print(f"Running Supabase tests...")
    asyncio.run(test_documents_table()) 