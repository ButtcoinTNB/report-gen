"""
Test script for the AIAgentLoop class
"""
# ruff: noqa: E402

import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_dir))

from backend.utils.agents_loop import AIAgentLoop

async def test_agent():
    """Test the AIAgentLoop initialization and basic functionality."""
    agent = AIAgentLoop(max_loops=3)
    print("AIAgentLoop initialized successfully")
    return agent

def main():
    """Run the async test."""
    asyncio.run(test_agent())

if __name__ == "__main__":
    main() 