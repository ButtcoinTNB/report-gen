"""
Script to check environment details on Render.
"""

import os
import sys

def check_environment():
    print("\n=== Environment Check ===")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.path}")
    
    print("\n=== File Check ===")
    try:
        # Check if models.py exists in the root directory
        if os.path.exists("models.py"):
            print("models.py exists in current directory")
            with open("models.py", "r") as f:
                first_line = f.readline().strip()
            print(f"First line of models.py: {first_line}")
        else:
            print("models.py does not exist in current directory")
            
        # Check if it exists in the backend directory
        if os.path.exists("backend/models.py"):
            print("backend/models.py exists")
        else:
            print("backend/models.py does not exist")
            
    except Exception as e:
        print(f"Error checking files: {e}")
    
    print("\n=== Directory Contents ===")
    for item in os.listdir("."):
        print(f"- {item}")

if __name__ == "__main__":
    check_environment() 