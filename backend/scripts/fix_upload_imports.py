#!/usr/bin/env python
"""
Script to fix imports in the upload.py file to use absolute import paths.
This ensures compatibility between local development and production environments.

Usage:
    python backend/scripts/fix_upload_imports.py
"""

import re
from pathlib import Path

# Path to the upload.py file
UPLOAD_FILE = Path(__file__).parent.parent / "api" / "upload.py"

def fix_upload_imports():
    """Fix imports in the upload.py file."""
    print(f"Fixing imports in {UPLOAD_FILE}")
    
    with open(UPLOAD_FILE, 'r') as f:
        content = f.read()
    
    # Replace all imports that need fixing
    # 1. Replace 'from utils.' with 'from backend.utils.'
    content = re.sub(r'from utils\.', 'from backend.utils.', content)
    
    # 2. Replace 'from api.' with 'from backend.api.'
    content = re.sub(r'from api\.', 'from backend.api.', content)
    
    # 3. Replace 'from config import' with 'from backend.config import'
    content = re.sub(r'from config import', 'from backend.config import', content)
    
    # 4. Import statements on their own line
    content = re.sub(r'import utils\.', 'import backend.utils.', content)
    content = re.sub(r'import api\.', 'import backend.api.', content)
    content = re.sub(r'import config\b', 'import backend.config', content)
    
    # Save the updated file
    with open(UPLOAD_FILE, 'w') as f:
        f.write(content)
    
    print("Fixed imports in upload.py to use absolute paths.")

if __name__ == '__main__':
    fix_upload_imports() 