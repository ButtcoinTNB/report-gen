#!/usr/bin/env python
"""
Environment Setup Script

This script helps set up environment variables for the application.
It copies the appropriate .env.example file to .env based on the specified environment.
"""

import os
import shutil
import argparse
from pathlib import Path

def get_project_root():
    """Get the project root directory"""
    # Assuming script is in backend/scripts
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = script_dir.parent
    project_root = backend_dir.parent
    return project_root

def setup_environment(env_type='local'):
    """
    Copy appropriate .env file based on environment
    
    Args:
        env_type: Environment type ('local', 'production')
    """
    project_root = get_project_root()
    backend_dir = project_root / 'backend'
    frontend_dir = project_root / 'frontend'
    
    # Source paths
    main_example = project_root / '.env.example'
    env_specific_example = project_root / f'.env.{env_type}.example'
    
    # Choose the right source file
    source = env_specific_example if env_specific_example.exists() else main_example
    
    if not source.exists():
        print(f"Error: Could not find {source}")
        return False
    
    # Set up backend .env
    backend_target = backend_dir / '.env'
    print(f"Copying {source} to {backend_target}")
    shutil.copy(source, backend_target)
    
    # Set up frontend .env.local
    frontend_target = frontend_dir / '.env.local'
    print(f"Copying {source} to {frontend_target}")
    
    # Filter only the NEXT_PUBLIC_ variables for frontend
    with open(source, 'r') as src_file, open(frontend_target, 'w') as dest_file:
        # First write a header
        dest_file.write("# Frontend environment variables\n")
        dest_file.write("# Auto-generated from .env.example\n\n")
        
        for line in src_file:
            # Only copy NEXT_PUBLIC_ variables and non-comment, non-empty lines
            if line.strip() and not line.strip().startswith('#') and 'NEXT_PUBLIC_' in line:
                dest_file.write(line)
    
    print(f"Environment configured for {env_type}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Set up environment variables')
    parser.add_argument('--env', default='local', choices=['local', 'production'],
                      help='Environment type (local, production)')
    args = parser.parse_args()
    
    if setup_environment(args.env):
        print("✅ Environment setup complete")
    else:
        print("❌ Environment setup failed") 