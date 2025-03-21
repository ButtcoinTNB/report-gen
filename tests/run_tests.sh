#!/bin/bash

# Set up colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Insurance Report Generator - Test Runner${NC}"
echo "====================================="

# Check if virtual environment exists, create it if it doesn't
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# First try with minimal requirements
echo -e "${YELLOW}Installing minimal dependencies...${NC}"
pip install -r minimal-requirements.txt

# Create test dirs if needed
mkdir -p tests/temp

# Try running the simple test first
echo -e "${GREEN}Running simplified test for FileProcessor chunked upload...${NC}"
echo "This test will verify basic functionality without external dependencies."

python backend/simple_test.py

# Check if the test succeeded
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Simple test completed successfully!${NC}"
else
    echo -e "${RED}Simple test failed. See errors above.${NC}"
fi

# Run the error handling tests
echo -e "${GREEN}Running error handling tests...${NC}"
echo "This test will verify the enhanced exception handling in the FileProcessor."

# Run the error handling tests with the correct Python module path
python -m backend.tests.test_error_handling

# Check if the test succeeded
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Error handling tests completed successfully!${NC}"
else
    echo -e "${RED}Error handling tests failed. See errors above.${NC}"
fi

echo -e "${YELLOW}Would you like to install all dependencies and run the full test suite? (y/n)${NC}"
read -r answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Installing all dependencies...${NC}"
    pip install -r requirements-dev.txt
    
    echo -e "${GREEN}Running complete test suite...${NC}"
    # Set PYTHONPATH to include backend directory (though it should be unnecessary with the module approach)
    export PYTHONPATH=$PYTHONPATH:$(pwd)/backend
    python -m pytest backend/tests/test_chunked_upload.py -v
else
    echo -e "${YELLOW}Skipping full test suite.${NC}"
fi

# Deactivate the virtual environment
deactivate

echo ""
echo -e "${YELLOW}Testing completed.${NC}"
echo ""
echo -e "${YELLOW}Troubleshooting:${NC}"
echo "1. If you're seeing import errors, ensure the virtual environment is activated:"
echo "   source venv/bin/activate"
echo ""
echo "2. You can run tests directly within the activated environment:"
echo "   python -m backend.tests.test_error_handling"
echo "   python -m backend.tests.test_chunked_upload"
echo ""
echo "3. If you're still having import issues, try running tests with the full module path:"
echo "   python -m backend.tests.test_chunked_upload"
echo ""
echo "4. To exit the virtual environment when done, type 'deactivate'"

exit 0 