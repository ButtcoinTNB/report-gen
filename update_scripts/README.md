# API Endpoint Update and Verification Scripts

This directory contains scripts to update and verify API endpoints for the Insurance Report Generator project.

## Overview

The Insurance Report Generator API has standardized its endpoints. These scripts help with:

1. **Updating Code**: Automatically find and replace old endpoint references with new ones
2. **Testing Endpoints**: Verify that endpoints work correctly according to documentation
3. **Documentation**: Ensure consistency between code and documentation

## Scripts

### `update_api_endpoints.py`

This Python script automatically finds and updates API endpoint references throughout the codebase.

#### Features:

- Updates Python files (router definitions, URL patterns)
- Updates JavaScript/TypeScript files (fetch calls, axios requests)
- Updates documentation files (markdown, etc.)
- Updates test files
- Generates a summary of all changes made

#### Usage:

```bash
# Make executable
chmod +x update_scripts/update_api_endpoints.py

# Run the script
./update_scripts/update_api_endpoints.py
```

#### Expected Output:

The script will show:
- Files being processed
- Endpoints being updated
- Summary of all changes made

### `verify_endpoints.js`

This JavaScript script verifies that API endpoints work correctly by making real requests to a running server.

#### Features:

- Tests all standardized endpoints
- Provides detailed output of successful and failed requests
- Saves test results to JSON files
- Color-coded terminal output

#### Prerequisites:

- Node.js installed
- Server running at http://localhost:8000
- Required npm packages: axios, form-data

#### Usage:

```bash
# Install dependencies if needed
npm install axios form-data

# Make executable
chmod +x update_scripts/verify_endpoints.js

# Run the script
node update_scripts/verify_endpoints.js
```

#### Expected Output:

The script will show:
- Endpoints being tested
- Success/failure status of each test
- Summary of all tests run
- Location of saved results file

## Endpoint Mapping Reference

The following table shows the mapping from old endpoints to new standardized endpoints:

| Old Endpoint | New Endpoint |
|--------------|--------------|
| `/api/upload/chunked/init` | `/api/uploads/initialize` |
| `/api/upload/chunked/{upload_id}` | `/api/uploads/chunk` |
| `/api/upload/chunked/{upload_id}/complete` | `/api/uploads/finalize` |
| `/api/upload` | `/api/uploads/initialize` |
| `/api/generate` | `/api/agent-loop/generate-report` |
| `/api/generate/status/{report_id}` | `/api/agent-loop/task-status/{task_id}` |
| `/api/generate/from-id` | `/api/agent-loop/generate-report` |
| `/api/edit/{report_id}` | `/api/agent-loop/refine-report` |
| `/api/generate/reports/{report_id}/files` | `/api/reports/{report_id}/files` |
| `/api/generate/reports/generate-docx` | `/api/reports/{report_id}/generate-docx` |
| `/api/generate/reports/{report_id}/refine` | `/api/agent-loop/refine-report` |

## Troubleshooting

### Connection Issues

If you see connection errors like `ECONNREFUSED`, make sure:
- The server is running on port 8000
- There are no firewalls blocking the connection

### Authentication Issues

If you see authentication errors:
- The API might require authentication tokens
- You may need to modify the scripts to include auth headers

### Update Issues

If the update script misses some references:
- Add the specific patterns to the script
- Report the issue in the project tracking system

## Contributing

To contribute to these scripts:

1. Test your changes thoroughly
2. Follow the existing code style
3. Document any new features or changes
4. Submit a pull request with a clear description

## License

These scripts are covered under the same license as the main project. 