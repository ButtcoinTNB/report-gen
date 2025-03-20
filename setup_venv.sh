#!/bin/bash

# Set up colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Insurance Report Generator - Setting up Virtual Environment${NC}"
echo "====================================="

# Create a virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
python3 -m venv venv

# Activate the virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install pydantic werkzeug python-magic

echo -e "${GREEN}Virtual environment setup complete!${NC}"
echo ""
echo -e "${YELLOW}To use the virtual environment:${NC}"
echo "1. Activate it with: source venv/bin/activate"
echo "2. Run tests with: python backend/simple_test.py"
echo ""
echo "To exit the virtual environment when done, type 'deactivate'"

# Stay in the activated environment
exec $SHELL 