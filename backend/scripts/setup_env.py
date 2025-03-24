#!/usr/bin/env python3
"""
Environment Variable Setup Script for Insurance Report Generator

This script automates the configuration of environment variables for both
backend and frontend components of the application by:

1. Copying the appropriate .env.example file to backend/.env
2. Creating a filtered version for frontend in frontend/.env.local

Usage:
    python backend/scripts/setup_env.py --env [local|production]
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# Define environment variable prefixes that should be included in frontend .env file
FRONTEND_PREFIXES = ["NEXT_PUBLIC_", "NODE_ENV", "DEBUG"]


def get_project_root():
    """Get the absolute path to the project root directory"""
    # Get the directory this script is in
    script_dir = Path(__file__).resolve().parent

    # Go up two levels (from /backend/scripts to project root)
    project_root = script_dir.parent.parent

    return project_root


def setup_environment(env_type="local"):
    """
    Set up environment variables for both backend and frontend

    Args:
        env_type: Type of environment ('local' or 'production')
    """
    project_root = get_project_root()

    # Define source and destination paths
    if env_type == "production":
        source_env = project_root / ".env.production.example"
    else:
        source_env = project_root / ".env.local.example"

    # If the specific example doesn't exist, fall back to the general one
    if not source_env.exists():
        source_env = project_root / ".env.example"

    backend_env = project_root / "backend" / ".env"
    frontend_env = project_root / "frontend" / ".env.local"

    if not source_env.exists():
        print(f"Error: Source environment file {source_env} not found.")
        sys.exit(1)

    # Create directories if they don't exist
    os.makedirs(project_root / "backend", exist_ok=True)
    os.makedirs(project_root / "frontend", exist_ok=True)

    # 1. Copy the source file to backend/.env
    print(f"Copying {source_env} to {backend_env}")
    shutil.copy2(source_env, backend_env)

    # 2. Create frontend/.env.local with filtered variables
    print(f"Creating filtered version for frontend in {frontend_env}")

    with open(source_env, "r") as source_file:
        frontend_lines = []

        for line in source_file:
            line = line.strip()

            # Skip empty lines and comments, but keep section headers
            if not line or (
                line.startswith("#")
                and "FRONTEND" not in line
                and "frontend" not in line.lower()
            ):
                continue

            # Include all comment lines with "frontend" in them
            if line.startswith("#") and (
                "FRONTEND" in line or "frontend" in line.lower()
            ):
                frontend_lines.append(line)
                continue

            # Include lines with frontend prefixes
            for prefix in FRONTEND_PREFIXES:
                if line.startswith(prefix + "=") or line.startswith(prefix + " ="):
                    frontend_lines.append(line)
                    break

    # Write frontend environment file
    with open(frontend_env, "w") as frontend_file:
        frontend_file.write("# Frontend Environment Variables\n")
        frontend_file.write("# Auto-generated from " + source_env.name + "\n\n")
        frontend_file.write("\n".join(frontend_lines))

    print("Environment setup complete!")
    print(f"- Backend: {backend_env}")
    print(f"- Frontend: {frontend_env}")
    print("\nNOTE: You should review these files and update values as needed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Set up environment variables for Insurance Report Generator"
    )
    parser.add_argument(
        "--env",
        default="local",
        choices=["local", "production"],
        help="Environment type (local or production)",
    )

    args = parser.parse_args()
    setup_environment(args.env)
