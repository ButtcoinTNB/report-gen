"""
Tests for the upload API endpoints to ensure they match documentation
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

# Try both import styles to handle different environments
try:
    from main import app
except ImportError:
    try:
        from backend.main import app
    except ImportError:
        pytest.skip("Could not import app", allow_module_level=True)

client = TestClient(app)

# Test data
TEST_FILENAME = "test_document.pdf"
TEST_FILESIZE = 1024
TEST_MIMETYPE = "application/pdf"
TEST_REPORT_ID = "test-report-123"


def test_initialize_upload():
    """Test the initialize upload endpoint"""
    response = client.post(
        "/api/uploads/initialize",
        data={
            "filename": TEST_FILENAME,
            "fileSize": TEST_FILESIZE,
            "mimeType": TEST_MIMETYPE,
            "reportId": TEST_REPORT_ID,
        },
    )
    
    # Should return 200 OK
    assert response.status_code == 200
    
    # Should return expected fields
    data = response.json()
    assert "uploadId" in data
    assert "chunkSize" in data
    assert "totalChunks" in data
    assert "uploadedChunks" in data
    assert data["resumable"] is True
    
    # Return the upload ID for subsequent tests
    return data["uploadId"]


def test_upload_chunk(tmp_path):
    """Test the upload chunk endpoint"""
    # First initialize an upload
    upload_id = test_initialize_upload()
    
    # Create a test file chunk
    chunk_content = b"This is test content for the chunk"
    chunk_path = tmp_path / "testchunk.bin"
    with open(chunk_path, "wb") as f:
        f.write(chunk_content)
    
    # Upload the chunk
    with open(chunk_path, "rb") as f:
        response = client.post(
            "/api/uploads/chunk",
            data={
                "uploadId": upload_id,
                "chunkIndex": 0,
                "start": 0,
                "end": len(chunk_content) - 1,
            },
            files={"chunk": ("testchunk.bin", f, "application/octet-stream")},
        )
    
    # Should return 200 OK
    assert response.status_code == 200
    
    # Should return expected fields
    data = response.json()
    assert "chunkIndex" in data
    assert data["chunkIndex"] == 0
    assert "received" in data
    assert data["received"] == len(chunk_content)
    
    # Return the upload ID for subsequent tests
    return upload_id


def test_finalize_upload():
    """Test the finalize upload endpoint"""
    # First upload a chunk
    upload_id = test_upload_chunk(tmp_path=pytest.tmp_path)
    
    # Finalize the upload
    response = client.post(
        "/api/uploads/finalize",
        data={
            "uploadId": upload_id,
            "filename": TEST_FILENAME,
            "reportId": TEST_REPORT_ID,
        },
    )
    
    # Should return 200 OK
    assert response.status_code == 200
    
    # Should return expected fields
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "fileId" in data["data"]
    assert "filename" in data["data"]
    assert data["data"]["filename"] == TEST_FILENAME
    
    # Return the file ID for subsequent tests
    return data["data"]["fileId"]


def test_cancel_upload():
    """Test the cancel upload endpoint"""
    # First initialize an upload
    upload_id = test_initialize_upload()
    
    # Cancel the upload
    response = client.post(
        "/api/uploads/cancel",
        data={
            "uploadId": upload_id,
        },
    )
    
    # Should return 200 OK
    assert response.status_code == 200
    
    # Should return expected fields
    data = response.json()
    assert data["status"] == "success"
    assert "message" in data["data"]
    assert "cancelled" in data["data"]["message"].lower()


def test_error_handling_invalid_upload_id():
    """Test error handling for invalid upload ID"""
    response = client.post(
        "/api/uploads/chunk",
        data={
            "uploadId": "non-existent-id",
            "chunkIndex": 0,
            "start": 0,
            "end": 100,
        },
        files={"chunk": ("testchunk.bin", b"test content", "application/octet-stream")},
    )
    
    # Should return 400 or 404
    assert response.status_code in (400, 404)
    
    # Should return error information
    data = response.json()
    assert data["status"] == "error" or "error" in data
    

def test_error_handling_large_file():
    """Test error handling for file size exceeding limit"""
    # Get the max upload size from settings or use a default
    from config import settings
    max_size = getattr(settings, "MAX_UPLOAD_SIZE", 1024 * 1024 * 1024)  # Default 1GB
    
    # Try to initialize an upload with a size exceeding the limit
    response = client.post(
        "/api/uploads/initialize",
        data={
            "filename": TEST_FILENAME,
            "fileSize": max_size + 1024,  # Exceed by 1KB
            "mimeType": TEST_MIMETYPE,
        },
    )
    
    # Should return 400 Bad Request
    assert response.status_code == 400
    
    # Should mention file size in the error
    data = response.json()
    assert "file" in data["detail"].lower() and "size" in data["detail"].lower() 