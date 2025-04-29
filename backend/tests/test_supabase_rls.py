"""
Test suite for Supabase RLS (Row Level Security) policies
"""
import os
import sys
import pytest
import asyncio
import uuid
from typing import Dict, Any

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings
from utils.supabase_helper import create_supabase_client, async_supabase_client_context

# Test data
TEST_USER = {
    "id": str(uuid.uuid4()),
    "email": "test@example.com"
}

TEST_DOCUMENT = {
    "filename": "test_document.pdf",
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

@pytest.fixture
async def supabase():
    """Fixture for Supabase client"""
    async with async_supabase_client_context() as client:
        yield client

@pytest.mark.asyncio
async def test_anonymous_access(supabase):
    """Test anonymous access to documents"""
    # 1. Try to insert a document without user
    doc_id = str(uuid.uuid4())
    result = await supabase.table("documents").insert({
        "id": doc_id,
        **TEST_DOCUMENT
    }).execute()
    
    # Should succeed for anonymous uploads
    assert not result.error
    
    # 2. Try to read the document
    result = await supabase.table("documents").select("*").eq("id", doc_id).execute()
    assert not result.error
    assert len(result.data) == 1
    
    # 3. Try to update the document
    result = await supabase.table("documents").update({
        "status": "processed"
    }).eq("id", doc_id).execute()
    
    # Should fail for anonymous users
    assert result.error is not None

@pytest.mark.asyncio
async def test_user_access(supabase):
    """Test user-specific access to documents"""
    # 1. Create a document with user ID
    doc_id = str(uuid.uuid4())
    result = await supabase.table("documents").insert({
        "id": doc_id,
        "created_by": TEST_USER["id"],
        **TEST_DOCUMENT
    }).execute()
    
    assert not result.error
    
    # 2. Try to read own document
    result = await supabase.table("documents").select("*").eq("id", doc_id).execute()
    assert not result.error
    assert len(result.data) == 1
    
    # 3. Try to update own document
    result = await supabase.table("documents").update({
        "status": "processed"
    }).eq("id", doc_id).execute()
    
    assert not result.error

@pytest.mark.asyncio
async def test_shared_access(supabase):
    """Test shared document access"""
    # 1. Create a document
    doc_id = str(uuid.uuid4())
    result = await supabase.table("documents").insert({
        "id": doc_id,
        "created_by": TEST_USER["id"],
        **TEST_DOCUMENT
    }).execute()
    
    assert not result.error
    
    # 2. Create a share record
    share_id = str(uuid.uuid4())
    result = await supabase.table("shared_documents").insert({
        "id": share_id,
        "document_id": doc_id,
        "shared_by": TEST_USER["id"],
        "access_type": "view"
    }).execute()
    
    assert not result.error
    
    # 3. Try to access document through share link
    result = await supabase.table("documents").select("*").eq("id", doc_id).execute()
    assert not result.error
    assert len(result.data) == 1

@pytest.mark.asyncio
async def test_template_access(supabase):
    """Test template access controls"""
    # 1. Create a template
    template_id = str(uuid.uuid4())
    result = await supabase.table("templates").insert({
        "id": template_id,
        "name": "Test Template",
        "description": "Test template description",
        "content": "Test template content",
        "created_by": TEST_USER["id"]
    }).execute()
    
    assert not result.error
    
    # 2. Try to read public template
    result = await supabase.table("templates").select("*").eq("id", template_id).execute()
    assert not result.error
    assert len(result.data) == 1
    
    # 3. Try to update template as owner
    result = await supabase.table("templates").update({
        "name": "Updated Template"
    }).eq("id", template_id).execute()
    
    assert not result.error

@pytest.mark.asyncio
async def test_report_access(supabase):
    """Test report access controls"""
    # 1. Create a report
    report_id = str(uuid.uuid4())
    result = await supabase.table("reports").insert({
        "id": report_id,
        "document_id": str(uuid.uuid4()),
        "created_by": TEST_USER["id"],
        "status": "completed",
        "content": "Test report content"
    }).execute()
    
    assert not result.error
    
    # 2. Try to read own report
    result = await supabase.table("reports").select("*").eq("id", report_id).execute()
    assert not result.error
    assert len(result.data) == 1
    
    # 3. Try to update own report
    result = await supabase.table("reports").update({
        "status": "archived"
    }).eq("id", report_id).execute()
    
    assert not result.error

@pytest.mark.asyncio
async def test_cross_user_access(supabase):
    """Test cross-user access restrictions"""
    # 1. Create documents for two different users
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())
    
    # Create first document
    result = await supabase.table("documents").insert({
        "id": doc1_id,
        "created_by": TEST_USER["id"],
        **TEST_DOCUMENT
    }).execute()
    
    assert not result.error
    
    # Create second document
    result = await supabase.table("documents").insert({
        "id": doc2_id,
        "created_by": str(uuid.uuid4()),  # Different user
        **TEST_DOCUMENT
    }).execute()
    
    assert not result.error
    
    # 2. Try to access other user's document
    result = await supabase.table("documents").select("*").eq("id", doc2_id).execute()
    
    # Should fail or return no results due to RLS
    assert len(result.data) == 0

if __name__ == "__main__":
    pytest.main([__file__]) 