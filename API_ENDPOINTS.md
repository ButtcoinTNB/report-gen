# Insurance Report Generator API Documentation

## Overview

This document provides a comprehensive guide to the Insurance Report Generator API, detailing endpoints, request/response formats, and common workflows. The API allows for document upload processing, report generation, and file management through a RESTful interface.

## Base URL

- Development: `http://localhost:8000`
- Production: Deployment-specific URL (see environment configuration)

## Authentication

The API supports both authenticated and unauthenticated access. Authentication is optional for most endpoints but provides additional functionality for user-specific operations.

**Authentication Headers:**
```
Authorization: Bearer {jwt_token}
```

## Standard Response Format

All endpoints return responses in a standardized format:

```json
{
  "status": "success",
  "data": { ... }  // Response data varies by endpoint
}
```

Error responses follow this format:

```json
{
  "status": "error",
  "message": "Error description",
  "code": "ERROR_CODE",
  "details": { ... }  // Additional error details (optional)
}
```

## Task Management Pattern

The API follows an asynchronous task pattern for long-running operations:

1. **Task Initiation**: An endpoint returns a `task_id`
2. **Task Monitoring**: The client tracks task progress using either:
   - **WebSocket**: Real-time updates via server-sent events
   - **Polling**: Regular status checks at an interval
3. **Task Completion**: Task status changes to "completed" with result data or "failed" with error details

## API Endpoints

### 1. File Upload and Management

#### Initialize Chunked Upload

Prepares the server for receiving a file in chunks, which is useful for large files.

**Endpoint:** `POST /api/uploads/initialize`  
**Content-Type:** `application/x-www-form-urlencoded`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| filename | String | Yes | Name of the file |
| fileSize | Number | Yes | Total size of the file in bytes |
| mimeType | String | Yes | MIME type of the file |
| reportId | String | No | ID of the report to associate with this file |

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/uploads/initialize" \
  -F "filename=document.pdf" \
  -F "fileSize=5242880" \
  -F "mimeType=application/pdf"
```

**Success Response:**
```json
{
  "uploadId": "upload_uuid",
  "chunkSize": 1048576,
  "totalChunks": 5,
  "uploadedChunks": [],
  "resumable": true
}
```

#### Upload Chunk

Uploads a single chunk of a file during a chunked upload process.

**Endpoint:** `POST /api/uploads/chunk`  
**Content-Type:** `multipart/form-data`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| uploadId | String | Yes | ID from initialization |
| chunkIndex | Number | Yes | Zero-based index of the chunk |
| start | Number | Yes | Start byte position |
| end | Number | Yes | End byte position |
| chunk | File | Yes | The chunk data |

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/uploads/chunk" \
  -F "uploadId=upload_uuid" \
  -F "chunkIndex=0" \
  -F "start=0" \
  -F "end=1048575" \
  -F "chunk=@chunk_file"
```

**Success Response:**
```json
{
  "chunkIndex": 0,
  "received": 1048576,
  "start": 0,
  "end": 1048575,
  "isComplete": true
}
```

#### Finalize Upload

Combines all chunks into the final file and makes it available for processing.

**Endpoint:** `POST /api/uploads/finalize`  
**Content-Type:** `application/x-www-form-urlencoded`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| uploadId | String | Yes | ID from initialization |
| filename | String | Yes | Final filename |
| reportId | String | No | ID of the report to associate with this file |

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/uploads/finalize" \
  -F "uploadId=upload_uuid" \
  -F "filename=document.pdf"
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "fileId": "file_uuid",
    "filename": "document.pdf",
    "size": 5242880,
    "mimeType": "application/pdf",
    "path": "uploads/file_uuid/document.pdf",
    "url": "/files/document.pdf"
  }
}
```

#### Cancel Upload

Cancels an in-progress chunked upload and cleans up temporary files.

**Endpoint:** `POST /api/uploads/cancel`  
**Content-Type:** `application/x-www-form-urlencoded`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| uploadId | String | Yes | ID of the upload to cancel |

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/uploads/cancel" \
  -F "uploadId=upload_uuid"
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "message": "Upload cancelled successfully"
  }
}
```

### 2. Agent Loop Processing

#### Generate Report

Creates a new report using the AI agent loop, taking document IDs as input.

**Endpoint:** `POST /api/agent-loop/generate-report`  
**Content-Type:** `application/json`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| insurance_data | Object | Yes | Insurance-related data for the report |
| document_ids | Array | Yes | Array of document IDs to include in the report |
| input_type | String | No | Type of input data (default: "insurance") |
| max_iterations | Number | No | Maximum number of AI iterations (default: 3) |
| template_type | String | No | Type of template to use (default: "standard") |
| user_id | String | No | ID of the user making the request |

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/agent-loop/generate-report" \
  -H "Content-Type: application/json" \
  -d '{
    "insurance_data": {
      "policy_number": "12345",
      "claim_number": "C-789456"
    },
    "document_ids": ["doc_uuid1", "doc_uuid2"],
    "input_type": "insurance",
    "max_iterations": 3
  }'
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "task_id": "task_uuid",
    "message": "Report generation started"
  }
}
```

#### Refine Report

Refines an existing report based on user feedback.

**Endpoint:** `POST /api/agent-loop/refine-report`  
**Content-Type:** `application/json`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| report_id | String | Yes | ID of the report to refine |
| feedback | String | Yes | User feedback for refinement |
| user_id | String | No | ID of the user making the request |

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/agent-loop/refine-report" \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report_uuid",
    "feedback": "Please add more details about water damage in section 3."
  }'
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "task_id": "task_uuid",
    "message": "Report refinement started"
  }
}
```

#### Get Task Status

Retrieves the current status of a task.

**Endpoint:** `GET /api/agent-loop/task-status/{task_id}`

**Path Parameters:**
- `task_id`: UUID of the task

**Query Parameters:**
- `user_id`: (Optional) User ID for verification

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/agent-loop/task-status/task_uuid"
```

**Success Response:**
```json
{
  "task_id": "task_uuid",
  "status": "in_progress",
  "progress": 65.5,
  "result": null,
  "error": null,
  "message": "Processing document 2 of 3",
  "stage": "writer",
  "estimated_time_remaining": 45
}
```

#### Subscribe to Task Updates (WebSocket)

Subscribes to real-time task updates using Server-Sent Events (SSE).

**Endpoint:** `GET /api/agent-loop/subscribe/{task_id}`

**Path Parameters:**
- `task_id`: UUID of the task

**Example Request:**
```bash
# Using JavaScript EventSource in a browser
const eventSource = new EventSource('http://localhost:8000/api/agent-loop/subscribe/task_uuid');
```

**Response:**
Server-sent events with the following format:
```
event: task_update
data: {"progress": 45.2, "message": "Writer agent generating content", "stage": "writing"}

event: task_complete
data: {"result": {...report data...}}

event: task_error
data: {"error": "Error message"}
```

#### Cancel Task

Cancels a running task.

**Endpoint:** `POST /api/agent-loop/cancel-task/{task_id}`

**Path Parameters:**
- `task_id`: UUID of the task

**Request Body:**
```json
{
  "userId": "user_uuid" // Optional
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/agent-loop/cancel-task/task_uuid"
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "message": "Task cancelled successfully"
  }
}
```

### 3. Report Management

#### Get Report Files

Retrieves all files associated with a specific report.

**Endpoint:** `GET /api/reports/{report_id}/files`

**Path Parameters:**
- `report_id`: UUID of the report

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/reports/report_uuid/files"
```

**Success Response:**
```json
{
  "status": "success",
  "data": [
    {
      "file_id": "file_uuid1",
      "filename": "document1.pdf",
      "file_size": 1048576,
      "mime_type": "application/pdf",
      "created_at": "2023-01-01T12:00:00Z"
    },
    {
      "file_id": "file_uuid2",
      "filename": "document2.jpg",
      "file_size": 524288,
      "mime_type": "image/jpeg",
      "created_at": "2023-01-01T12:05:00Z"
    }
  ]
}
```

#### Generate DOCX Report

Creates a DOCX document from a report ID.

**Endpoint:** `POST /api/reports/{report_id}/generate-docx`

**Path Parameters:**
- `report_id`: UUID of the report

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/reports/report_uuid/generate-docx"
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "report_id": "report_uuid",
    "docx_url": "/reports/report_uuid.docx"
  }
}
```

#### Download Report

Downloads the generated report document.

**Endpoint:** `GET /api/reports/{report_id}/download`

**Path Parameters:**
- `report_id`: UUID of the report

**Query Parameters:**
- `format`: "docx" or "pdf" (defaults to "docx")

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/reports/report_uuid/download" --output report.docx
```

**Response:**
The actual file as a binary download

### 4. Document Operations

#### Get Document Metadata

Retrieves metadata for a document.

**Endpoint:** `GET /api/documents/{document_id}/metadata`

**Path Parameters:**
- `document_id`: UUID of the document

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/documents/doc_uuid/metadata"
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "id": "doc_uuid",
    "filename": "insurance_policy.pdf",
    "size": 1048576,
    "content_type": "application/pdf",
    "status": "processed",
    "quality_score": 0.85,
    "pages": 15,
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-01-01T12:10:00Z"
  }
}
```

#### Update Document Metadata

Updates metadata for a specific document.

**Endpoint:** `PATCH /api/documents/{document_id}/metadata`

**Path Parameters:**
- `document_id`: UUID of the document

**Request Body:**
```json
{
  "filename": "updated_filename.pdf",
  "status": "reviewed",
  "quality_score": 0.9,
  "pages": 16
}
```

**Example Request:**
```bash
curl -X PATCH "http://localhost:8000/api/documents/doc_uuid/metadata" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "updated_filename.pdf",
    "status": "reviewed"
  }'
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "id": "doc_uuid",
    "filename": "updated_filename.pdf",
    "size": 1048576,
    "content_type": "application/pdf",
    "status": "reviewed",
    "quality_score": 0.9,
    "pages": 16,
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-01-01T12:15:00Z"
  }
}
```

## Common Workflows

### Complete File Upload and Report Generation Flow

1. **Initialize Chunked Upload:**
   ```bash
   curl -X POST "http://localhost:8000/api/uploads/initialize" \
     -F "filename=document.pdf" \
     -F "fileSize=5242880" \
     -F "mimeType=application/pdf"
   ```

2. **Upload Chunks (Repeat for Each Chunk):**
   ```bash
   curl -X POST "http://localhost:8000/api/uploads/chunk" \
     -F "uploadId=upload_uuid" \
     -F "chunkIndex=0" \
     -F "start=0" \
     -F "end=1048575" \
     -F "chunk=@chunk_file"
   ```

3. **Finalize Upload:**
   ```bash
   curl -X POST "http://localhost:8000/api/uploads/finalize" \
     -F "uploadId=upload_uuid" \
     -F "filename=document.pdf"
   ```

4. **Generate Report (Initiate Task):**
   ```bash
   curl -X POST "http://localhost:8000/api/agent-loop/generate-report" \
     -H "Content-Type: application/json" \
     -d '{
       "insurance_data": {"policy_number": "12345"},
       "document_ids": ["file_uuid"]
     }'
   ```

5. **Monitor Task Status (Polling):**
   ```bash
   curl "http://localhost:8000/api/agent-loop/task-status/task_uuid"
   ```

   **Alternative: Use WebSocket for Real-Time Updates:**
   Connect to `ws://localhost:8000/api/agent-loop/subscribe/task_uuid`

6. **Generate DOCX when Task Completes:**
   ```bash
   curl -X POST "http://localhost:8000/api/reports/report_uuid/generate-docx"
   ```

7. **Download Final Report:**
   ```bash
   curl "http://localhost:8000/api/reports/report_uuid/download" --output report.docx
   ```

### Report Refinement Flow

1. **Submit Refinement Request:**
   ```bash
   curl -X POST "http://localhost:8000/api/agent-loop/refine-report" \
     -H "Content-Type: application/json" \
     -d '{
       "report_id": "report_uuid",
       "feedback": "Please add more details about water damage in section 3."
     }'
   ```

2. **Monitor Refinement Task Status:**
   ```bash
   curl "http://localhost:8000/api/agent-loop/task-status/task_uuid"
   ```

3. **Download Refined Report:**
   ```bash
   curl "http://localhost:8000/api/reports/report_uuid/download" --output refined_report.docx
   ```

## Error Handling

Common error codes:

| Code | Description |
|------|-------------|
| INVALID_INPUT | The request contains invalid input data |
| FILE_NOT_FOUND | The requested file could not be found |
| REPORT_NOT_FOUND | The requested report could not be found |
| TASK_NOT_FOUND | The requested task could not be found |
| PROCESSING_ERROR | An error occurred during processing |
| UNAUTHORIZED | Authentication is required for this operation |
| INTERNAL_ERROR | An unexpected internal error occurred |

## Rate Limiting

The API implements rate limiting to prevent abuse:

- Standard endpoints: 60 requests per minute
- Resource-intensive endpoints (report generation, refinement): Stricter limits

Rate limit headers in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 58
X-RateLimit-Reset: 1743151560
```

## Deprecated Endpoints

The following endpoints are deprecated and will be removed in future versions:

1. **`POST /api/upload`**: Use `/api/uploads/initialize` and chunked upload flow instead
2. **`POST /api/generate`**: Use `/api/agent-loop/generate-report` instead
3. **`GET /api/generate/status/{report_id}`**: Use `/api/agent-loop/task-status/{task_id}` instead
4. **`POST /api/generate/from-id`**: Use `/api/agent-loop/generate-report` instead
5. **`POST /api/edit/{report_id}`**: Use `/api/agent-loop/refine-report` instead
6. **`POST /api/upload/chunked/init`**: Use `/api/uploads/initialize` instead
7. **`POST /api/upload/chunked/{upload_id}`**: Use `/api/uploads/chunk` instead
8. **`POST /api/upload/chunked/{upload_id}/complete`**: Use `/api/uploads/finalize` instead
9. **`GET /api/generate/reports/{report_id}/files`**: Use `/api/reports/{report_id}/files` instead
10. **`POST /api/generate/reports/generate-docx`**: Use `/api/reports/{report_id}/generate-docx` instead
11. **`POST /api/generate/reports/{report_id}/refine`**: Use `/api/agent-loop/refine-report` instead

## Known Issues and Limitations

1. Report generation for very large documents (>100MB) may timeout - use chunked uploads for large files
2. The API currently handles up to 10 concurrent report generation tasks
3. File types are limited to: PDF, DOCX, DOC, TXT, JPG, JPEG, PNG
4. Maximum file size: 1GB (configurable via environment variables)

## Environment Variables

Key environment variables that affect API behavior:

- `SUPABASE_URL` and `SUPABASE_KEY`: Database and auth configuration
- `OPENROUTER_API_KEY`: AI model access
- `MAX_UPLOAD_SIZE`: Maximum file size (default: 1GB)
- `API_RATE_LIMIT`: Rate limit for API calls
- `CORS_ALLOW_ALL`: Whether to allow all origins for CORS

## Database Schema Integration

The API interacts with several key database tables in Supabase:

- `files`: Stores file metadata and references
- `reports`: Stores report data and processing status
- `tasks`: Tracks background processing tasks

### Key Relationships:
- Reports have many-to-many relationship with files through `document_ids` field
- Tasks reference reports through `report_id` field
- Files can be standalone or associated with reports 