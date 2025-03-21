#!/bin/bash

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements-dev.txt

echo "Testing environment setup complete."
echo ""
echo "To run tests, use:"
echo "source venv/bin/activate"
echo "cd backend"
echo "python -m pytest tests/test_chunked_upload.py -v"
echo ""
echo "For more detailed output with coverage:"
echo "python -m pytest tests/test_chunked_upload.py -v --cov=utils" 