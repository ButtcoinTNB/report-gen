#!/usr/bin/env python
"""
Test script for the /from-id endpoint.
Verifies behavior with valid, missing, and invalid report IDs.

Usage:
    python test_from_id.py [base_url]

Arguments:
    base_url: Optional. Base URL of the API. Default: http://localhost:8000
"""

import sys
import requests
import json
import uuid
from typing import Dict, Any, Optional


def test_from_id_endpoint(base_url: str = "http://localhost:8000") -> None:
    """Test the /from-id endpoint with different scenarios."""
    endpoint = f"{base_url}/api/generate/from-id"
    headers = {"Content-Type": "application/json"}
    
    # Case 1: Test with missing report_id
    print("\n\033[1m== Test with missing report_id ==\033[0m")
    response = requests.post(endpoint, headers=headers, json={})
    print_response(response)
    
    # Case 2: Test with invalid report_id format
    print("\n\033[1m== Test with invalid report_id format ==\033[0m")
    response = requests.post(endpoint, headers=headers, json={"report_id": "not-a-valid-uuid"})
    print_response(response)
    
    # Case 3: Test with non-existent report_id (valid UUID but doesn't exist)
    print("\n\033[1m== Test with non-existent report_id ==\033[0m")
    random_uuid = str(uuid.uuid4())
    response = requests.post(endpoint, headers=headers, json={"report_id": random_uuid})
    print_response(response)
    
    # Case 4: Prompt for a valid report_id to test
    valid_id = input("\nEnter a valid report_id to test (or press Enter to skip): ").strip()
    if valid_id:
        print(f"\n\033[1m== Test with valid report_id: {valid_id} ==\033[0m")
        response = requests.post(endpoint, headers=headers, json={"report_id": valid_id})
        print_response(response)


def print_response(response: requests.Response) -> None:
    """Print the response details in a formatted way."""
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    try:
        json_response = response.json()
        print("\nResponse Body:")
        print(json.dumps(json_response, indent=2))
    except json.JSONDecodeError:
        print("\nResponse Body (non-JSON):")
        print(response.text[:500])  # Print first 500 chars to avoid overwhelming output
        if len(response.text) > 500:
            print("...")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
    
    print(f"Testing /from-id endpoint at {base_url}")
    test_from_id_endpoint(base_url) 