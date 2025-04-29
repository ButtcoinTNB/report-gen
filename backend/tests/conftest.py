import os
import sys
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from backend.main import app
from backend.utils.supabase_helper import create_supabase_client
from backend.config import TEST_USER

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_client():
    """Create a test client for testing."""
    client = TestClient(app)
    return client

@pytest_asyncio.fixture
async def async_client():
    """Create an async client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

@pytest_asyncio.fixture
async def supabase():
    """Create a test Supabase client."""
    client = await create_supabase_client()
    await client.auth.sign_in_with_password({
        "email": TEST_USER["email"],
        "password": TEST_USER["password"]
    })
    await client.auth.get_session()  # Ensure session is established
    
    # Need to yield the actual client, not the async generator
    yield client
    
    # Clean up after test
    await client.auth.sign_out() 