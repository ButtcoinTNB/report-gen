# backend/scripts/register_reference_pdfs.py
import os
import sys
import requests
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config import settings

# Path to reference reports
reference_dir = Path(__file__).parent.parent / "reference_reports"

# Supabase API headers
headers = {
    "apikey": settings.SUPABASE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def register_pdf(pdf_path):
    """Register a PDF file in the Supabase database"""
    filename = os.path.basename(pdf_path)
    name = os.path.splitext(filename)[0]
    
    # You might want to extract text from the PDF here
    # For simplicity, we're just registering the file path
    
    data = {
        "name": name,
        "file_path": str(pdf_path),
        "is_reference": True
    }
    
    response = requests.post(
        f"{settings.SUPABASE_URL}/rest/v1/reference_reports",
        headers=headers,
        json=data
    )
    
    if response.status_code in (200, 201):
        print(f"Successfully registered {filename}")
    else:
        print(f"Failed to register {filename}: {response.text}")

def main():
    for file in reference_dir.glob("*.pdf"):
        register_pdf(file)
    
if __name__ == "__main__":
    main()