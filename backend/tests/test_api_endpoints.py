"""
Test suite for API endpoints and Supabase integration
"""
import os
import sys
import pytest
import uuid

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import settings

# Test data
TEST_FILE_CONTENT = b"Test file content"
TEST_DOCUMENT = {
    "filename": "test_document.pdf",
    "content_type": "application/pdf",
    "size": len(TEST_FILE_CONTENT),
    "status": "uploaded",
    "quality_score": 0,
    "edit_count": 0,
    "iterations": 0,
    "time_saved": 0,
    "download_count": 0,
    "pages": 1
}

@pytest.mark.asyncio
async def test_health_check(async_client):
    """Test health check endpoint"""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_chunked_upload_flow(async_client, supabase):
    """Test the complete chunked upload flow"""
    # 1. Initialize upload
    upload_data = {
        "filename": TEST_DOCUMENT["filename"],
        "fileSize": TEST_DOCUMENT["size"],
        "mimeType": TEST_DOCUMENT["content_type"]
    }
    response = await async_client.post("/api/uploads/initialize", data=upload_data)
    assert response.status_code == 200
    upload_id = response.json()["uploadId"]

    # 2. Upload chunk
    chunk_data = {
        "uploadId": upload_id,
        "chunkIndex": 0,
        "start": 0,
        "end": len(TEST_FILE_CONTENT) - 1
    }
    files = {"chunk": ("chunk", TEST_FILE_CONTENT)}
    response = await async_client.post("/api/uploads/chunk", data=chunk_data, files=files)
    assert response.status_code == 200

    # 3. Finalize upload
    finalize_data = {
        "uploadId": upload_id,
        "filename": TEST_DOCUMENT["filename"]
    }
    response = await async_client.post("/api/uploads/finalize", data=finalize_data)
    assert response.status_code == 200
    file_id = response.json()["data"]["fileId"]

    # 4. Verify in Supabase
    result = await supabase.table("documents").select("*").eq("id", file_id).execute()
    assert not result.error
    assert len(result.data) == 1
    assert result.data[0]["filename"] == TEST_DOCUMENT["filename"]

@pytest.mark.asyncio
async def test_report_generation(async_client, supabase):
    """Test report generation flow"""
    # 1. Create a document first
    doc_id = str(uuid.uuid4())
    result = await supabase.table("documents").insert({
        "id": doc_id,
        **TEST_DOCUMENT
    }).execute()
    assert not result.error

    # 2. Start report generation
    response = await async_client.post(f"/api/reports/generate/{doc_id}")
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    # 3. Check report status
    response = await async_client.get(f"/api/reports/status/{task_id}")
    assert response.status_code == 200
    assert response.json()["status"] in ["pending", "processing", "completed", "failed"]

@pytest.mark.asyncio
async def test_document_sharing(async_client, supabase):
    """Test document sharing functionality"""
    # 1. Create a document
    doc_id = str(uuid.uuid4())
    result = await supabase.table("documents").insert({
        "id": doc_id,
        **TEST_DOCUMENT
    }).execute()
    assert not result.error

    # 2. Create share link
    response = await async_client.post(f"/api/share/create/{doc_id}")
    assert response.status_code == 200
    share_id = response.json()["share_id"]

    # 3. Verify share link
    response = await async_client.get(f"/api/share/verify/{share_id}")
    assert response.status_code == 200
    assert response.json()["document_id"] == doc_id

@pytest.mark.asyncio
async def test_template_management(async_client, supabase):
    """Test template management"""
    # 1. Create template
    template_data = {
        "name": "Test Template",
        "description": "Test template description",
        "content": "Test template content"
    }
    response = await async_client.post("/api/templates/", json=template_data)
    assert response.status_code == 200
    template_id = response.json()["id"]

    # 2. Get template
    response = await async_client.get(f"/api/templates/{template_id}")
    assert response.status_code == 200
    assert response.json()["name"] == template_data["name"]

    # 3. Update template
    update_data = {
        "name": "Updated Template",
        "description": "Updated description",
        "content": "Updated content"
    }
    response = await async_client.put(f"/api/templates/{template_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == update_data["name"]

    # 4. Delete template
    response = await async_client.delete(f"/api/templates/{template_id}")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_error_handling(async_client):
    """Test error handling"""
    # 1. Test 404
    response = await async_client.get("/api/nonexistent")
    assert response.status_code == 404

    # 2. Test invalid file upload
    response = await async_client.post("/api/uploads/initialize", data={})
    assert response.status_code == 422

    # 3. Test invalid report generation
    response = await async_client.post("/api/reports/generate/invalid-id")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_rate_limiting(async_client):
    """Test rate limiting"""
    # Make multiple rapid requests
    responses = []
    for _ in range(settings.API_RATE_LIMIT + 1):
        response = await async_client.get("/health")
        responses.append(response.status_code)

    # At least one request should be rate limited
    assert 429 in responses

if __name__ == "__main__":
    pytest.main([__file__])