#!/bin/bash

# Set up colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Insurance Report Generator - Test Runner${NC}"
echo "====================================="

# First try with minimal requirements
echo -e "${YELLOW}Installing minimal dependencies...${NC}"
pip3 install -r minimal-requirements.txt

# Create test dirs if needed
mkdir -p tests/temp

# Try running the simple test first
echo -e "${GREEN}Running simplified test for FileProcessor chunked upload...${NC}"
echo "This test will verify basic functionality without external dependencies."

python3 backend/simple_test.py

# Check if the test succeeded
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Simple test completed successfully!${NC}"
else
    echo -e "${RED}Simple test failed. See errors above.${NC}"
fi

echo -e "${YELLOW}Would you like to install all dependencies and run the full test suite? (y/n)${NC}"
read -r answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Installing all dependencies...${NC}"
    pip3 install -r requirements-dev.txt
    
    echo -e "${GREEN}Running complete test suite...${NC}"
    python3 -m pytest backend/tests/test_chunked_upload.py -v
else
    echo -e "${YELLOW}Skipping full test suite.${NC}"
fi

echo ""
echo -e "${YELLOW}Testing completed.${NC}"
echo ""
echo -e "${YELLOW}Troubleshooting:${NC}"
echo "1. If you're seeing import errors, you may need to install these libraries:"
echo "   pip3 install pydantic werkzeug python-magic"
echo ""
echo "2. For the full test suite, you'll need these additional libraries:"
echo "   pip3 install fastapi pytest pytest-asyncio python-multipart pillow pymupdf"
echo ""
echo "3. You can run the simplified test directly with:"
echo "   python3 backend/simple_test.py"

exit 0 