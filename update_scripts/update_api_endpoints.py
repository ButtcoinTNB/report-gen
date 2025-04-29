#!/usr/bin/env python3
"""
Endpoint Update Script for Insurance Report Generator

This script updates all API endpoint references in the codebase to ensure
they match the documentation. It handles:

1. Code files (Python/JS): Updates endpoint references in handlers and tests
2. Documentation files: Ensures consistency across documentation
3. Test files: Updates API test scripts

Usage: python update_scripts/update_api_endpoints.py
"""

import os
import re
import json
import glob
from typing import Dict, List, Tuple, Set, Optional, Any
from pathlib import Path

# Define the project root directory
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Color formatting for terminal output
COLORS = {
    "HEADER": "\033[95m",
    "BLUE": "\033[94m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "ENDC": "\033[0m",
    "BOLD": "\033[1m",
}

# Endpoint mapping - from old endpoints to new standardized endpoints
ENDPOINT_MAPPING = {
    # Upload endpoints
    "/api/upload/chunked/init": "/api/uploads/initialize",
    "/api/upload/chunked/{upload_id}": "/api/uploads/chunk",
    "/api/upload/chunked/{upload_id}/complete": "/api/uploads/finalize",
    "/api/upload": "/api/uploads/initialize",  # Direct upload is now chunked
    
    # Agent loop endpoints
    "/api/generate": "/api/agent-loop/generate-report",
    "/api/generate/status/{report_id}": "/api/agent-loop/task-status/{task_id}",
    "/api/generate/from-id": "/api/agent-loop/generate-report",
    "/api/edit/{report_id}": "/api/agent-loop/refine-report",
    
    # Report endpoints
    "/api/generate/reports/{report_id}/files": "/api/reports/{report_id}/files",
    "/api/generate/reports/generate-docx": "/api/reports/{report_id}/generate-docx",
    "/api/generate/reports/{report_id}/refine": "/api/agent-loop/refine-report",
}

# Files to exclude from processing
EXCLUDED_FILES = {
    ".git",
    "node_modules",
    "venv",
    "__pycache__",
    ".ruff_cache",
    ".dccache",
    ".DS_Store",
}

# Track changes for reporting
changes_made: Dict[str, List[str]] = {
    "python": [],
    "javascript": [],
    "documentation": [],
    "tests": [],
}


def print_color(text: str, color: str = "BLUE", bold: bool = False) -> None:
    """Print colored text to the console"""
    color_code = COLORS[color]
    bold_code = COLORS["BOLD"] if bold else ""
    end_code = COLORS["ENDC"]
    print(f"{bold_code}{color_code}{text}{end_code}")


def find_files(extensions: List[str], excluded_dirs: Optional[Set[str]] = None) -> List[Path]:
    """Find all files with given extensions, excluding specified directories"""
    if excluded_dirs is None:
        excluded_dirs = EXCLUDED_FILES
        
    all_files: List[Path] = []
    
    for ext in extensions:
        pattern = f"**/*.{ext}"
        for file_path in PROJECT_ROOT.glob(pattern):
            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in excluded_dirs):
                continue
            all_files.append(file_path)
    
    return all_files


def update_python_files() -> None:
    """Update endpoint references in Python files"""
    print_color("Updating Python files...", "HEADER", True)
    
    # Find all Python files
    python_files = find_files(["py"])
    
    # Regular expressions for finding endpoint patterns
    router_pattern = re.compile(r'@router\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]')
    url_pattern = re.compile(r'(url|endpoint)\s*=\s*[\'"]([^\'"]+)[\'"]')
    string_url_pattern = re.compile(r'[\'"](/api/[^\'"]+)[\'"]')
    
    for file_path in python_files:
        # Skip this script itself
        if file_path.name == os.path.basename(__file__):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        # Replace endpoints in router decorators
        for method, endpoint in router_pattern.findall(content):
            if endpoint in ENDPOINT_MAPPING:
                new_endpoint = ENDPOINT_MAPPING[endpoint]
                content = content.replace(f'@router.{method}("{endpoint}"', f'@router.{method}("{new_endpoint}"')
                content = content.replace(f"@router.{method}('{endpoint}'", f"@router.{method}('{new_endpoint}'")
        
        # Replace endpoints in URL assignments
        for var, endpoint in url_pattern.findall(content):
            if endpoint in ENDPOINT_MAPPING:
                new_endpoint = ENDPOINT_MAPPING[endpoint]
                content = content.replace(f'{var}="{endpoint}"', f'{var}="{new_endpoint}"')
                content = content.replace(f"{var}='{endpoint}'", f"{var}='{new_endpoint}'")
        
        # Try to find other endpoint strings in the file
        for endpoint in string_url_pattern.findall(content):
            if endpoint in ENDPOINT_MAPPING:
                new_endpoint = ENDPOINT_MAPPING[endpoint]
                content = content.replace(f'"{endpoint}"', f'"{new_endpoint}"')
                content = content.replace(f"'{endpoint}'", f"'{new_endpoint}'")
        
        # If changes were made, write the file
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            relative_path = file_path.relative_to(PROJECT_ROOT)
            changes_made["python"].append(str(relative_path))
            print_color(f"  Updated: {relative_path}", "GREEN")


def update_javascript_files() -> None:
    """Update endpoint references in JavaScript and TypeScript files"""
    print_color("Updating JavaScript/TypeScript files...", "HEADER", True)
    
    # Find all JS/TS files
    js_files = find_files(["js", "jsx", "ts", "tsx"])
    
    # Regular expressions for finding endpoint patterns
    fetch_pattern = re.compile(r'(fetch|axios\.(get|post|put|delete)|api\.(get|post|put|delete))\s*\(\s*[\'"`]([^\'"`]+)[\'"`]')
    url_pattern = re.compile(r'(url|endpoint|apiUrl|path)\s*[:=]\s*[\'"`]([^\'"`]+)[\'"`]')
    string_url_pattern = re.compile(r'[\'"`](/api/[^\'"`]+)[\'"`]')
    
    for file_path in js_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace endpoints in fetch/axios calls
        for match in fetch_pattern.finditer(content):
            full_match = match.group(0)
            endpoint = match.group(4)
            
            # Only process if it's an API endpoint
            if endpoint.startswith('/api/'):
                for old_endpoint, new_endpoint in ENDPOINT_MAPPING.items():
                    # Handle wildcard endpoints by converting to regex pattern
                    old_pattern = old_endpoint.replace('{', '(?P<').replace('}', '>[^/]+)')
                    regex = re.compile(f'^{old_pattern}$')
                    
                    if regex.match(endpoint):
                        # Extract parameters from the old endpoint
                        match_obj = regex.match(endpoint)
                        if match_obj:
                            # Get named groups from the match
                            params = match_obj.groupdict()
                            replaced_endpoint = new_endpoint
                            
                            # Replace parameters in the new endpoint
                            for param_name, param_value in params.items():
                                replaced_endpoint = replaced_endpoint.replace(f'{{{param_name}}}', param_value)
                            
                            # Replace in the content
                            new_full_match = full_match.replace(endpoint, replaced_endpoint)
                            content = content.replace(full_match, new_full_match)
                            break
                        elif endpoint == old_endpoint:
                            # Direct replacement
                            new_full_match = full_match.replace(endpoint, new_endpoint)
                            content = content.replace(full_match, new_full_match)
                            break
        
        # Replace endpoints in URL assignments
        for var, endpoint in url_pattern.findall(content):
            if endpoint.startswith('/api/'):
                for old_endpoint, new_endpoint in ENDPOINT_MAPPING.items():
                    # Handle wildcard endpoints by converting to regex pattern
                    old_pattern = old_endpoint.replace('{', '(?P<').replace('}', '>[^/]+)')
                    regex = re.compile(f'^{old_pattern}$')
                    
                    if regex.match(endpoint):
                        # Extract parameters from the old endpoint
                        match_obj = regex.match(endpoint)
                        if match_obj:
                            # Get named groups from the match
                            params = match_obj.groupdict()
                            replaced_endpoint = new_endpoint
                            
                            # Replace parameters in the new endpoint
                            for param_name, param_value in params.items():
                                replaced_endpoint = replaced_endpoint.replace(f'{{{param_name}}}', param_value)
                            
                            # Replace in the content
                            content = content.replace(f'{var}: "{endpoint}"', f'{var}: "{replaced_endpoint}"')
                            content = content.replace(f"{var}: '{endpoint}'", f"{var}: '{replaced_endpoint}'")
                            content = content.replace(f'{var}="{endpoint}"', f'{var}="{replaced_endpoint}"')
                            content = content.replace(f"{var}='{endpoint}'", f"{var}='{replaced_endpoint}'")
                            break
                        elif endpoint == old_endpoint:
                            # Direct replacement
                            content = content.replace(f'{var}: "{endpoint}"', f'{var}: "{new_endpoint}"')
                            content = content.replace(f"{var}: '{endpoint}'", f"{var}: '{new_endpoint}'")
                            content = content.replace(f'{var}="{endpoint}"', f'{var}="{new_endpoint}"')
                            content = content.replace(f"{var}='{endpoint}'", f"{var}='{new_endpoint}'")
                            break
        
        # Try to find other endpoint strings in the file
        for url in string_url_pattern.findall(content):
            if url.startswith('/api/'):
                for old_endpoint, new_endpoint in ENDPOINT_MAPPING.items():
                    # Handle wildcard endpoints
                    old_pattern = old_endpoint.replace('{', '(?P<').replace('}', '>[^/]+)')
                    regex = re.compile(f'^{old_pattern}$')
                    
                    if regex.match(url):
                        # Extract parameters from the old endpoint
                        match_obj = regex.match(url)
                        if match_obj:
                            # Get named groups from the match
                            params = match_obj.groupdict()
                            replaced_endpoint = new_endpoint
                            
                            # Replace parameters in the new endpoint
                            for param_name, param_value in params.items():
                                replaced_endpoint = replaced_endpoint.replace(f'{{{param_name}}}', param_value)
                            
                            # Replace in the content
                            content = content.replace(f'"{url}"', f'"{replaced_endpoint}"')
                            content = content.replace(f"'{url}'", f"'{replaced_endpoint}'")
                            content = content.replace(f"`{url}`", f"`{replaced_endpoint}`")
                            break
                        elif url == old_endpoint:
                            # Direct replacement
                            content = content.replace(f'"{url}"', f'"{new_endpoint}"')
                            content = content.replace(f"'{url}'", f"'{new_endpoint}'")
                            content = content.replace(f"`{url}`", f"`{new_endpoint}`")
                            break
        
        # If changes were made, write the file
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            relative_path = file_path.relative_to(PROJECT_ROOT)
            changes_made["javascript"].append(str(relative_path))
            print_color(f"  Updated: {relative_path}", "GREEN")


def update_documentation_files() -> None:
    """Update endpoint references in documentation files"""
    print_color("Updating documentation files...", "HEADER", True)
    
    # Find all documentation files
    doc_files = find_files(["md", "mdx", "txt", "rst"])
    
    for file_path in doc_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace all deprecated endpoints in documentation
        for old_endpoint, new_endpoint in ENDPOINT_MAPPING.items():
            # For documentation, we care about exact string matches
            # We may need to handle URL params differently for docs
            
            # Remove param placeholders for readability
            clean_old = old_endpoint.replace('{', '').replace('}', '')
            clean_new = new_endpoint.replace('{', '').replace('}', '')
            
            # Replace in backticks (code blocks)
            content = content.replace(f'`{old_endpoint}`', f'`{new_endpoint}`')
            content = content.replace(f'`{clean_old}`', f'`{clean_new}`')
            
            # Replace in code examples
            content = content.replace(f'"{old_endpoint}"', f'"{new_endpoint}"')
            content = content.replace(f"'{old_endpoint}'", f"'{new_endpoint}'")
            
            # Replace in URLs
            content = content.replace(f'/{clean_old}', f'/{clean_new}')
            
            # Special handling for curl examples
            content = content.replace(f'curl -X GET "{old_endpoint}', f'curl -X GET "{new_endpoint}')
            content = content.replace(f'curl -X POST "{old_endpoint}', f'curl -X POST "{new_endpoint}')
            content = content.replace(f'curl -X PUT "{old_endpoint}', f'curl -X PUT "{new_endpoint}')
            content = content.replace(f'curl -X DELETE "{old_endpoint}', f'curl -X DELETE "{new_endpoint}')
            
            # Replace in headers
            content = content.replace(f'**Endpoint:** `{old_endpoint}`', f'**Endpoint:** `{new_endpoint}`')
            content = content.replace(f'**Endpoint:** `{clean_old}`', f'**Endpoint:** `{clean_new}`')
        
        # If changes were made, write the file
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            relative_path = file_path.relative_to(PROJECT_ROOT)
            changes_made["documentation"].append(str(relative_path))
            print_color(f"  Updated: {relative_path}", "GREEN")


def update_test_files() -> None:
    """Update endpoint references in test files"""
    print_color("Updating test files...", "HEADER", True)
    
    # Find all test files
    test_files = find_files(["py", "js", "ts"])
    test_files = [f for f in test_files if "test" in f.name.lower() or "tests" in str(f)]
    
    for file_path in test_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Regular expressions for finding endpoint patterns in tests
        url_pattern = re.compile(r'(client\.(get|post|put|patch|delete)|fetch|axios\.(get|post|put|delete))\s*\(\s*[\'"`]([^\'"`]+)[\'"`]')
        string_url_pattern = re.compile(r'[\'"`](/api/[^\'"`]+)[\'"`]')
        
        # Replace endpoints in API client calls
        for match in url_pattern.finditer(content):
            full_match = match.group(0)
            endpoint = match.group(4)
            
            if endpoint.startswith('/api/'):
                for old_endpoint, new_endpoint in ENDPOINT_MAPPING.items():
                    # Handle wildcard endpoints
                    old_pattern = old_endpoint.replace('{', '(?P<').replace('}', '>[^/]+)')
                    regex = re.compile(f'^{old_pattern}$')
                    
                    if regex.match(endpoint):
                        # Extract parameters from the old endpoint
                        match_obj = regex.match(endpoint)
                        if match_obj:
                            # Get named groups from the match
                            params = match_obj.groupdict()
                            replaced_endpoint = new_endpoint
                            
                            # Replace parameters in the new endpoint
                            for param_name, param_value in params.items():
                                replaced_endpoint = replaced_endpoint.replace(f'{{{param_name}}}', param_value)
                            
                            # Replace in the content
                            new_full_match = full_match.replace(endpoint, replaced_endpoint)
                            content = content.replace(full_match, new_full_match)
                            break
                        elif endpoint == old_endpoint:
                            # Direct replacement
                            new_full_match = full_match.replace(endpoint, new_endpoint)
                            content = content.replace(full_match, new_full_match)
                            break
        
        # Try to find other endpoint strings in the file
        for url in string_url_pattern.findall(content):
            if url.startswith('/api/'):
                for old_endpoint, new_endpoint in ENDPOINT_MAPPING.items():
                    # Handle wildcard endpoints
                    old_pattern = old_endpoint.replace('{', '(?P<').replace('}', '>[^/]+)')
                    regex = re.compile(f'^{old_pattern}$')
                    
                    if regex.match(url):
                        # Extract parameters from the old endpoint
                        match_obj = regex.match(url)
                        if match_obj:
                            # Get named groups from the match
                            params = match_obj.groupdict()
                            replaced_endpoint = new_endpoint
                            
                            # Replace parameters in the new endpoint
                            for param_name, param_value in params.items():
                                replaced_endpoint = replaced_endpoint.replace(f'{{{param_name}}}', param_value)
                            
                            # Replace in the content
                            content = content.replace(f'"{url}"', f'"{replaced_endpoint}"')
                            content = content.replace(f"'{url}'", f"'{replaced_endpoint}'")
                            content = content.replace(f"`{url}`", f"`{replaced_endpoint}`")
                            break
                        elif url == old_endpoint:
                            # Direct replacement
                            content = content.replace(f'"{url}"', f'"{new_endpoint}"')
                            content = content.replace(f"'{url}'", f"'{new_endpoint}'")
                            content = content.replace(f"`{url}`", f"`{new_endpoint}`")
                            break
        
        # If changes were made, write the file
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            relative_path = file_path.relative_to(PROJECT_ROOT)
            changes_made["tests"].append(str(relative_path))
            print_color(f"  Updated: {relative_path}", "GREEN")


def update_api_test_script() -> None:
    """Update the API test script with the correct endpoints"""
    print_color("Updating main API test script...", "HEADER", True)
    
    test_script_path = PROJECT_ROOT / "tests" / "api_test.js"
    
    if not test_script_path.exists():
        print_color("  Warning: API test script not found", "YELLOW")
        return
    
    with open(test_script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Replace endpoint references for initialize upload
    content = content.replace(
        "'/api/upload/chunked/init'", 
        "'/api/uploads/initialize'"
    )
    content = content.replace(
        "'/api/uploads/chunked/init'", 
        "'/api/uploads/initialize'"
    )
    
    # Replace endpoint references for upload chunk
    content = content.replace(
        "'/api/upload/chunked/'", 
        "'/api/uploads/chunk'"
    )
    content = content.replace(
        "'/api/uploads/chunked/'", 
        "'/api/uploads/chunk'"
    )
    
    # Replace endpoint references for finalize upload
    content = content.replace(
        "'/api/upload/chunked/complete'", 
        "'/api/uploads/finalize'"
    )
    content = content.replace(
        "'/api/uploads/chunked/complete'", 
        "'/api/uploads/finalize'"
    )
    
    # Replace endpoint references for agent loop
    content = content.replace(
        "'/api/generate'", 
        "'/api/agent-loop/generate-report'"
    )
    content = content.replace(
        "'/api/generate/status/'", 
        "'/api/agent-loop/task-status/'"
    )
    
    # If changes were made, write the file
    if content != original_content:
        with open(test_script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        relative_path = test_script_path.relative_to(PROJECT_ROOT)
        changes_made["tests"].append(str(relative_path))
        print_color(f"  Updated: {relative_path}", "GREEN")


def update_python_test_files() -> None:
    """Update the Python test files with the correct endpoints"""
    print_color("Updating Python test files...", "HEADER", True)
    
    api_test_files = [
        PROJECT_ROOT / "tests" / "api" / "test_uploads_api.py",
        PROJECT_ROOT / "tests" / "api" / "test_agent_loop_api.py",
    ]
    
    for test_file_path in api_test_files:
        if not test_file_path.exists():
            print_color(f"  Warning: Test file not found: {test_file_path.name}", "YELLOW")
            continue
        
        with open(test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Update test endpoints based on the file
        if "test_uploads_api.py" in str(test_file_path):
            # Fix upload API test endpoints
            content = content.replace(
                '"/api/upload/chunked/init"', 
                '"/api/uploads/initialize"'
            )
            content = content.replace(
                '"/api/uploads/chunked/init"', 
                '"/api/uploads/initialize"'
            )
            content = content.replace(
                '"/api/upload/chunked/{upload_id}"', 
                '"/api/uploads/chunk"'
            )
            content = content.replace(
                '"/api/uploads/chunked/{upload_id}"', 
                '"/api/uploads/chunk"'
            )
            content = content.replace(
                '"/api/upload/chunked/{upload_id}/complete"', 
                '"/api/uploads/finalize"'
            )
            content = content.replace(
                '"/api/uploads/chunked/{upload_id}/complete"', 
                '"/api/uploads/finalize"'
            )
        
        elif "test_agent_loop_api.py" in str(test_file_path):
            # Fix agent loop API test endpoints
            content = content.replace(
                '"/api/generate"', 
                '"/api/agent-loop/generate-report"'
            )
            content = content.replace(
                '"/api/generate/status/', 
                '"/api/agent-loop/task-status/'
            )
            content = content.replace(
                '"/api/edit/', 
                '"/api/agent-loop/refine-report/'
            )
        
        # If changes were made, write the file
        if content != original_content:
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            relative_path = test_file_path.relative_to(PROJECT_ROOT)
            changes_made["tests"].append(str(relative_path))
            print_color(f"  Updated: {relative_path}", "GREEN")


def print_summary() -> None:
    """Print a summary of all changes made"""
    print_color("\nEndpoint Update Summary", "HEADER", True)
    
    total_changes = sum(len(changes) for changes in changes_made.values())
    
    if total_changes == 0:
        print_color("No changes were made. All endpoints are already up to date.", "GREEN")
        return
    
    print_color(f"Total files updated: {total_changes}", "BLUE", True)
    
    for category, files in changes_made.items():
        if files:
            print_color(f"\n{category.capitalize()} files ({len(files)}):", "BLUE", True)
            for file in files:
                print(f"  - {file}")


def main():
    """Main function to run all updates"""
    print_color("Starting API Endpoint Update Process", "HEADER", True)
    print_color("This script will update all API endpoints to match the documentation.\n", "BLUE")
    
    # Update different file types
    update_python_files()
    update_javascript_files()
    update_documentation_files()
    update_test_files()
    
    # Special handling for specific test files
    update_api_test_script()
    update_python_test_files()
    
    # Print summary of changes
    print_summary()


if __name__ == "__main__":
    main()
