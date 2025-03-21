#!/bin/bash

# Set up colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Insurance Report Generator - Running Tests in Virtual Environment${NC}"
echo "====================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Setting it up first...${NC}"
    ./setup_venv.sh
    exit 0
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Run the test
echo -e "${GREEN}Running simplified file processor test...${NC}"
python backend/simple_test.py

# Return to normal shell prompt
echo -e "${YELLOW}Test completed.${NC}" 