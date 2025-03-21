#!/bin/bash

# Set up colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Insurance Report Generator - macOS Environment Setup${NC}"
echo "====================================="

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo -e "${RED}Homebrew is not installed. It's required to install system dependencies.${NC}"
    echo "Please install Homebrew first: https://brew.sh/"
    exit 1
fi

# Install libmagic using Homebrew
echo -e "${YELLOW}Installing libmagic (system dependency)...${NC}"
brew install libmagic

# Create a virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
python3 -m venv venv

# Activate the virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install pydantic werkzeug python-magic PyMuPDF Pillow docx2txt pytest fastapi python-multipart httpx pydantic-settings uvicorn

echo -e "${GREEN}Environment setup complete!${NC}"
echo ""
echo -e "${YELLOW}To run tests:${NC}"
echo "1. Activate the environment: source venv/bin/activate"
echo "2. Run the simple test: python backend/simple_test.py"
echo "3. Run the full tests: python -m pytest backend/tests/test_chunked_upload.py -v"
echo ""
echo "Note: To exit the virtual environment when done, type 'deactivate'" 