"""
Script to automatically fix imports in Python files.
This will replace all instances of 'from X import' with 'from X import'.
"""

import os
import re
import sys

def fix_imports_in_file(file_path):
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Check if file has any imports from backend
        if 'from backend.' not in content:
            print(f"No backend imports in {file_path}, skipping")
            return 0
            
        # Replace 'from X import Y' with 'from X import Y'
        new_content = re.sub(r'from\s+backend\.(\w+)', r'from \1', content)
        
        # Count changes
        changes = content.count('from backend.') - new_content.count('from backend.')
        
        # Only write the file if changes were made
        if changes > 0:
            with open(file_path, 'w') as file:
                file.write(new_content)
            print(f"Fixed {changes} imports in {file_path}")
        else:
            print(f"No changes needed in {file_path}")
            
        return changes
    except Exception as e:
        print(f"Error fixing imports in {file_path}: {e}")
        return 0

def fix_imports_in_directory(directory):
    """Fix imports in all Python files in a directory and its subdirectories."""
    total_changes = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                total_changes += fix_imports_in_file(file_path)
    return total_changes

if __name__ == "__main__":
    # If no arguments provided, fix imports in current directory
    if len(sys.argv) < 2:
        directory = "."
    else:
        directory = sys.argv[1]
        
    print(f"Fixing imports in {directory}...")
    
    total_changes = fix_imports_in_directory(directory)
    
    print(f"Fixed a total of {total_changes} imports.")
    
    # Special case: check api/generate.py specifically
    generate_py = "api/generate.py"
    if os.path.exists(generate_py):
        print(f"\nSpecifically checking {generate_py}...")
        with open(generate_py, 'r') as file:
            content = file.readlines()
            for i, line in enumerate(content, 1):
                if 'from ' in line and 'models import' in line:
                    print(f"Line {i}: {line.strip()}")
    else:
        print(f"\n{generate_py} not found in current directory")
        
        # Try with backend prefix
        backend_generate_py = "backend/api/generate.py"
        if os.path.exists(backend_generate_py):
            print(f"Found {backend_generate_py}, checking...")
            with open(backend_generate_py, 'r') as file:
                content = file.readlines()
                for i, line in enumerate(content, 1):
                    if 'from ' in line and 'models import' in line:
                        print(f"Line {i}: {line.strip()}") 