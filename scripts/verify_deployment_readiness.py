#!/usr/bin/env python3
"""
Verify Deployment Readiness Script

This script checks whether the Insurance Report Generator application
is ready for deployment by verifying:
1. Backend package dependencies
2. Frontend package dependencies
3. Environment variables
4. File structure
5. Import statements
"""

import os
import sys
import json
import re
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
ENDC = "\033[0m"
BOLD = "\033[1m"

def print_status(message, status, details=None):
    """Print a status message with color formatting"""
    status_colors = {
        "PASS": GREEN + "PASS" + ENDC,
        "WARN": YELLOW + "WARN" + ENDC,
        "FAIL": RED + "FAIL" + ENDC,
        "INFO": BLUE + "INFO" + ENDC
    }
    
    formatted_status = status_colors.get(status, status)
    print(f"[{formatted_status}] {message}")
    
    if details:
        if isinstance(details, list):
            for detail in details:
                print(f"       {detail}")
        else:
            print(f"       {details}")
    print()

def find_project_root():
    """Find the project root directory"""
    # Start with the current directory
    current_dir = Path(os.getcwd())
    
    # Look for common project root indicators
    root_indicators = [
        "requirements.txt",
        "frontend/package.json",
        "backend/main.py"
    ]
    
    # Check current and parent directories for indicators
    for directory in [current_dir] + list(current_dir.parents):
        if any((directory / indicator).exists() for indicator in root_indicators):
            return directory
    
    # If we can't find a project root, use the current directory
    return current_dir

def check_backend_dependencies():
    """Check backend dependencies for compatibility"""
    project_root = find_project_root()
    requirements_path = project_root / "requirements.txt"
    
    if not requirements_path.exists():
        print_status(
            "Backend requirements.txt not found", 
            "FAIL", 
            f"Expected at: {requirements_path}"
        )
        return False
    
    # Check for key dependencies
    required_packages = {
        "fastapi": "FastAPI framework",
        "uvicorn": "ASGI server",
        "pydantic": "Data validation",
        "python-dotenv": "Environment variable management",
        "sqlalchemy": "Database ORM",
    }
    
    with open(requirements_path, "r") as f:
        requirements_content = f.read()
    
    missing_packages = []
    for package, description in required_packages.items():
        if not re.search(rf"{package}(?:==|>=|<=|~=|>|<)", requirements_content):
            missing_packages.append(f"{package} - {description}")
    
    if missing_packages:
        print_status(
            "Missing key backend dependencies", 
            "FAIL", 
            missing_packages
        )
        return False
    else:
        print_status("Backend dependencies check", "PASS", "All key dependencies found")
        return True

def check_frontend_dependencies():
    """Check frontend dependencies for compatibility"""
    project_root = find_project_root()
    package_json_path = project_root / "frontend" / "package.json"
    
    if not package_json_path.exists():
        print_status(
            "Frontend package.json not found", 
            "FAIL", 
            f"Expected at: {package_json_path}"
        )
        return False
    
    try:
        with open(package_json_path, "r") as f:
            package_data = json.load(f)
    except json.JSONDecodeError:
        print_status(
            "Frontend package.json is not valid JSON", 
            "FAIL"
        )
        return False
    
    # Check for key dependencies
    required_packages = {
        "next": "Next.js framework",
        "react": "React library",
        "react-dom": "React DOM",
        "typescript": "TypeScript",
        "@types/node": "Node.js type definitions",
        "@types/react": "React type definitions",
        "react-simplemde-editor": "Markdown editor component"
    }
    
    dependencies = {
        **package_data.get("dependencies", {}),
        **package_data.get("devDependencies", {})
    }
    
    missing_packages = []
    for package, description in required_packages.items():
        if package not in dependencies:
            missing_packages.append(f"{package} - {description}")
    
    if missing_packages:
        print_status(
            "Missing key frontend dependencies", 
            "FAIL", 
            missing_packages
        )
        return False
    else:
        print_status("Frontend dependencies check", "PASS", "All key dependencies found")
        return True

def check_environment_files():
    """Check for environment files and variables"""
    project_root = find_project_root()
    backend_env_path = project_root / "backend" / ".env"
    frontend_env_path = project_root / "frontend" / ".env.local"
    env_example_path = project_root / "backend" / ".env.example"
    
    # Check for .env and .env.example files
    backend_env_exists = backend_env_path.exists()
    frontend_env_exists = frontend_env_path.exists()
    env_example_exists = env_example_path.exists()
    
    if not backend_env_exists:
        print_status(
            "Backend .env file missing", 
            "WARN", 
            f"Expected at: {backend_env_path}"
        )
    
    if not frontend_env_exists:
        print_status(
            "Frontend .env.local file missing", 
            "WARN", 
            f"Expected at: {frontend_env_path}"
        )
    
    if not env_example_exists:
        print_status(
            "Backend .env.example file missing", 
            "WARN", 
            f"Expected at: {env_example_path}"
        )
    
    # Check if .env files are in .gitignore
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            gitignore_content = f.read()
        
        if ".env" not in gitignore_content:
            print_status(
                ".env files not in .gitignore", 
                "FAIL", 
                "Add .env to .gitignore to prevent committing sensitive data"
            )
    else:
        print_status(
            ".gitignore file missing", 
            "WARN", 
            "Create a .gitignore file to exclude sensitive files"
        )
    
    # Check for required environment variables in .env.example
    if env_example_exists:
        with open(env_example_path, "r") as f:
            env_example_content = f.read()
        
        required_vars = [
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "UPLOAD_DIR",
            "CORS_ALLOW_ORIGINS"
        ]
        
        missing_vars = []
        for var in required_vars:
            if var not in env_example_content:
                missing_vars.append(var)
        
        if missing_vars:
            print_status(
                "Missing required environment variables in .env.example", 
                "WARN", 
                missing_vars
            )
        else:
            print_status("Environment variables in .env.example", "PASS", "All required variables found")
    
    return backend_env_exists or env_example_exists

def check_import_statements():
    """Check for absolute import statements in Python files"""
    project_root = find_project_root()
    backend_dir = project_root / "backend"
    
    if not backend_dir.exists():
        print_status(
            "Backend directory not found", 
            "FAIL", 
            f"Expected at: {backend_dir}"
        )
        return False
    
    # Get all Python files in the backend directory
    python_files = list(backend_dir.rglob("*.py"))
    
    # Check for relative imports that might cause issues
    problematic_imports = []
    for file_path in python_files:
        with open(file_path, "r") as f:
            try:
                content = f.read()
                
                # Look for imports that don't start with "backend."
                # but import from a module that's part of the backend package
                # Exclude standard library imports
                relative_imports = re.findall(r"from\s+(api|utils|config|models|services)\s+import", content)
                
                if relative_imports:
                    relative_path = file_path.relative_to(project_root)
                    problematic_imports.append(f"{relative_path}: using relative imports {', '.join(relative_imports)}")
            except UnicodeDecodeError:
                # Skip binary files
                continue
    
    if problematic_imports:
        print_status(
            "Found potentially problematic relative imports", 
            "WARN", 
            problematic_imports[:5] + (["..."] if len(problematic_imports) > 5 else [])
        )
        return False
    else:
        print_status("Import statements check", "PASS", "No problematic relative imports found")
        return True

def check_file_structure():
    """Check for required directories and files"""
    project_root = find_project_root()
    
    required_dirs = [
        "backend",
        "frontend",
        "docs"
    ]
    
    required_files = [
        "README.md",
        "backend/main.py",
        "frontend/package.json"
    ]
    
    missing_dirs = []
    for directory in required_dirs:
        if not (project_root / directory).exists():
            missing_dirs.append(directory)
    
    missing_files = []
    for file in required_files:
        if not (project_root / file).exists():
            missing_files.append(file)
    
    if missing_dirs:
        print_status(
            "Missing required directories", 
            "FAIL", 
            missing_dirs
        )
    else:
        print_status("Directory structure check", "PASS", "All required directories found")
    
    if missing_files:
        print_status(
            "Missing required files", 
            "FAIL", 
            missing_files
        )
    else:
        print_status("File structure check", "PASS", "All required files found")
    
    return not (missing_dirs or missing_files)

def check_typescript_config():
    """Check for TypeScript configuration in the frontend"""
    project_root = find_project_root()
    tsconfig_path = project_root / "frontend" / "tsconfig.json"
    
    if not tsconfig_path.exists():
        print_status(
            "TypeScript configuration file missing", 
            "FAIL", 
            f"Expected at: {tsconfig_path}"
        )
        return False
    
    try:
        with open(tsconfig_path, "r") as f:
            tsconfig_data = json.load(f)
    except json.JSONDecodeError:
        print_status(
            "tsconfig.json is not valid JSON", 
            "FAIL"
        )
        return False
    
    # Check for key TypeScript configuration
    compiler_options = tsconfig_data.get("compilerOptions", {})
    
    required_options = [
        "target",
        "lib",
        "module",
        "moduleResolution",
        "jsx"
    ]
    
    missing_options = []
    for option in required_options:
        if option not in compiler_options:
            missing_options.append(option)
    
    if missing_options:
        print_status(
            "Missing key TypeScript compiler options", 
            "WARN", 
            missing_options
        )
        return False
    else:
        print_status("TypeScript configuration check", "PASS", "All key compiler options found")
        return True

def main():
    """Main function to run all checks"""
    print(BOLD + "Insurance Report Generator - Deployment Readiness Check" + ENDC)
    print("=" * 60 + "\n")
    
    all_checks_passed = True
    
    # Check backend dependencies
    backend_deps_ok = check_backend_dependencies()
    all_checks_passed = all_checks_passed and backend_deps_ok
    
    # Check frontend dependencies
    frontend_deps_ok = check_frontend_dependencies()
    all_checks_passed = all_checks_passed and frontend_deps_ok
    
    # Check environment files
    env_files_ok = check_environment_files()
    all_checks_passed = all_checks_passed and env_files_ok
    
    # Check import statements
    imports_ok = check_import_statements()
    all_checks_passed = all_checks_passed and imports_ok
    
    # Check file structure
    structure_ok = check_file_structure()
    all_checks_passed = all_checks_passed and structure_ok
    
    # Check TypeScript configuration
    ts_config_ok = check_typescript_config()
    all_checks_passed = all_checks_passed and ts_config_ok
    
    print("=" * 60)
    if all_checks_passed:
        print(GREEN + BOLD + "✅ All checks passed! The application is ready for deployment." + ENDC)
    else:
        print(RED + BOLD + "❌ Some checks failed. Please address the issues before deployment." + ENDC)
    
    return 0 if all_checks_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 