#!/bin/bash

# Activate the virtual environment
source ../venv/bin/activate

# Run the initialization script
python init_supabase.py

echo ""
echo "Next step: Upload reference PDFs using the /upload/template endpoint"
echo "Example using curl:"
echo "curl -X POST http://localhost:8000/upload/template -F \"name=Insurance Example\" -F \"file=@/path/to/your/reference.pdf\""
echo "" 