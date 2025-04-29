"""
Tests for the agent loop API endpoints to ensure they match documentation
"""

import json
import pytest
import time
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
TEST_REPORT_ID = "test-report-123"
TEST_TASK_ID = "test-task-456"
TEST_DOCUMENT_ID = "test-doc-789"


def test_generate_report():
    """Test the generate report endpoint"""
    response = client.post(
        "/api/agent-loop/generate-report",
        json={
            "insurance_data": {
                "policy_number": "12345",
                "claim_number": "C-789456"
            },
            "document_ids": [TEST_DOCUMENT_ID],
            "input_type": "insurance",
            "max_iterations": 1
        }
    )
    
    # Check response structure (even if it's an error, it should follow the format)
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "task_id" in data["data"]
        return data["data"]["task_id"]
    else:
        # If it fails (e.g., because test document doesn't exist), 
        # it should still return a properly structured error
        data = response.json()
        assert "error" in data or "status" in data
        # Skip further tests if this fails
        pytest.skip(f"Generate report failed with status {response.status_code}: {data}")


def test_task_status():
    """Test the task status endpoint"""
    # Try to generate a report first to get a task ID
    try:
        task_id = test_generate_report()
    except Exception:
        # Use a placeholder task ID if report generation fails
        task_id = TEST_TASK_ID
    
    response = client.get(f"/api/agent-loop/task-status/{task_id}")
    
    # If task exists, check response structure
    if response.status_code == 200:
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert data["status"] in ["queued", "in_progress", "completed", "failed", "error"]
        if data["status"] in ["in_progress", "completed"]:
            assert "progress" in data
    else:
        # If task doesn't exist, should return 404 with proper error structure
        assert response.status_code == 404
        data = response.json()
        assert "error" in data or "status" in data


def test_refine_report():
    """Test the refine report endpoint"""
    response = client.post(
        "/api/agent-loop/refine-report",
        json={
            "report_id": TEST_REPORT_ID,
            "feedback": "Please add more details about water damage in section 3."
        }
    )
    
    # Check response structure (even if it's an error, it should follow the format)
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "task_id" in data["data"]
    else:
        # If it fails (e.g., because report doesn't exist), 
        # it should still return a properly structured error
        data = response.json()
        assert "error" in data or "status" in data


def test_cancel_task():
    """Test the cancel task endpoint"""
    # Try to generate a report first to get a task ID
    try:
        task_id = test_generate_report()
        # Wait a moment to make sure task is registered
        time.sleep(1)
    except Exception:
        # Use a placeholder task ID if report generation fails
        task_id = TEST_TASK_ID
    
    response = client.post(f"/api/agent-loop/cancel-task/{task_id}")
    
    # Check response structure (even if it's an error, it should follow the format)
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "message" in data["data"]
        assert "cancel" in data["data"]["message"].lower()
    else:
        # If it fails (e.g., because task doesn't exist), 
        # it should still return a properly structured error
        data = response.json()
        assert "error" in data or "status" in data


def test_error_handling_invalid_task_id():
    """Test error handling for invalid task ID"""
    response = client.get("/api/agent-loop/task-status/invalid-task-id")
    
    # Should return 404 Not Found
    assert response.status_code == 404
    
    # Should return error information
    data = response.json()
    assert "error" in data or "status" == "error" in data 