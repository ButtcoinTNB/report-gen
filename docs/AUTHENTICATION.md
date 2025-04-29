# Authentication & Security Documentation

## Authentication Overview

The Insurance Report Generator implements a flexible authentication system that allows for both authenticated and unauthenticated access. This approach is designed to balance security with ease of use during the initial project phase.

### Current Implementation

- **Authentication Method**: JWT-based authentication using `OAuth2PasswordBearer`
- **Current Status**: Development mode with mock authentication (auto-creates test user)
- **Future Plan**: Full JWT implementation with proper user registration and management

## Endpoint Authentication Requirements

### Critical Endpoints with Required Authentication

These endpoints handle sensitive operations and require authentication:

- **`/api/generate/from-structure`** - Creating structured reports from templates
- **`/api/reports/generate-docx`** - Generating final DOCX files

### Endpoints with Optional Authentication

These endpoints function with or without authentication, but associate data with user accounts when authenticated:

- **`/api/upload/documents`** - Uploading case documents
- **`/api/generate/generate`** - Generating report content
- **`/api/agent-loop/generate-report`** - Retrieving report by ID
- **`/api/generate/analyze`** - Analyzing document content

### Public Endpoints

These endpoints are intentionally public for ease of use and don't require authentication:

- **`/api/download/{report_id}`** - Downloading generated reports
  - Justification: Reports are only accessible with the correct UUID, which acts as a de-facto access token
- **`/api/simple-test`** - Simple endpoint for testing connectivity
  - Justification: No sensitive operations, used for health checks

## File Path Security

To prevent path traversal attacks and other file system vulnerabilities, we've implemented several security measures:

1. **Path Validation**
   - All file paths are normalized and validated against a base directory
   - Paths that attempt to traverse outside allowed directories are rejected

2. **UUID Format Validation**
   - Report IDs and document IDs must conform to UUID format
   - This prevents injection of malicious path strings

3. **Safe Path Construction**
   - Helper functions ensure all file operations use validated paths
   - Example: `get_safe_file_path()` prevents directory traversal

## Development vs. Production

- **Development**: Currently using mock authentication
- **Production**: Will implement full JWT authentication with:
  - User registration/login
  - Token expiration and refresh
  - Role-based access control

## Recommendations for Future Enhancement

1. **Implement User Registration/Login**
   - Add user database tables
   - Create registration and login endpoints

2. **Add Role-Based Access Control**
   - Admin vs. Standard User permissions
   - Team-based access for collaborative reports

3. **Enable HTTPS Only**
   - Ensure all API communication uses HTTPS
   - Set Secure and HttpOnly flags for cookies

4. **Add Rate Limiting**
   - Prevent brute-force attacks
   - Implement per-user and per-IP request limiting

5. **Audit Logging**
   - Add comprehensive logging of authentication events
   - Create audit trails for sensitive operations 