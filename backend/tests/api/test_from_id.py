#!/usr/bin/env python
"""
Tests for the /from-id endpoint.
Verifies behavior with valid, missing, and invalid report IDs.

Usage:
    pytest backend/tests/api/test_from_id.py
"""

import uuid

import pytest
import requests

# Skip tests if host is not available
pytestmark = pytest.mark.skipif(
    requests.get("http://localhost:8000", timeout=2).status_code != 200,
    reason="API server is not running",
)


def test_missing_report_id():
    """Test behavior when report_id is missing from request."""
    endpoint = "http://localhost:8000/api/generate/from-id"
    headers = {"Content-Type": "application/json"}

    response = requests.post(endpoint, headers=headers, json={})
    assert response.status_code == 400
    assert "report_id" in response.text.lower()


def test_invalid_report_id_format():
    """Test behavior with invalid report_id format."""
    endpoint = "http://localhost:8000/api/generate/from-id"
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        endpoint, headers=headers, json={"report_id": "not-a-valid-uuid"}
    )
    assert response.status_code == 400
    assert "invalid" in response.text.lower()


def test_nonexistent_report_id():
    """Test behavior with non-existent report_id (valid UUID that doesn't exist)."""
    endpoint = "http://localhost:8000/api/generate/from-id"
    headers = {"Content-Type": "application/json"}

    random_uuid = str(uuid.uuid4())
    response = requests.post(endpoint, headers=headers, json={"report_id": random_uuid})
    assert response.status_code == 404
    assert "not found" in response.text.lower()


# This test requires a valid report ID to be provided
@pytest.mark.skip(reason="Requires a valid report ID to be provided")
def test_valid_report_id(valid_report_id):
    """Test behavior with a valid report ID."""
    endpoint = "http://localhost:8000/api/generate/from-id"
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        endpoint, headers=headers, json={"report_id": valid_report_id}
    )
    assert response.status_code == 200
    assert "content" in response.json()
