# Insurance Report Generator API Documentation

This API enables the generation, editing, and downloading of insurance reports based on document analysis. The system allows uploading various document types, processing them through AI models, and generating structured insurance reports.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://[domain]` (as configured in `.env` file)

## Authentication

Currently, the API uses rate limiting for protection. Future versions will implement JWT authentication.

## Standard Response Format

All endpoints return responses in a consistent format:

```json
{
  "status": "success|error",
  "data": { ... },  // For successful responses
  "code": "ERROR_CODE",  // For error responses
  "message": "Human-readable message",  // For error responses
  "details": { ... }  // Additional error details (optional)
}
```

## Error Handling

The API uses HTTP status codes and consistent error response formats:

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - The request was invalid |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 413 | Payload Too Large - File size exceeds limit |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Something went wrong |
| 503 | Service Unavailable - External service unavailable |

## API Endpoints

### Document Upload

Upload documents for report generation.

**Endpoint:** `POST /api/upload`  
**Content-Type:** `multipart/form-data`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| files | File | Yes | One or more files to upload (PDF, DOCX, JPG, PNG) |
| metadata | JSON | No | Additional metadata about the documents |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "files=@document1.pdf" \
  -F "files=@document2.jpg" \
  -F 'metadata={"case_number": "12345", "client_name": "Example Inc."}'
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "files": [
      {
        "file_id": "550e8400-e29b-41d4-a716-446655440000",
        "filename": "document1.pdf",
        "file_size": 1024567,
        "mime_type": "application/pdf"
      },
      {
        "file_id": "550e8400-e29b-41d4-a716-446655440001",
        "filename": "document2.jpg",
        "file_size": 253467,
        "mime_type": "image/jpeg"
      }
    ],
    "report_id": "550e8400-e29b-41d4-a716-446655440010"
  }
}
```

### Chunked Upload

For large files, the API supports chunked uploads.

**Endpoint:** `POST /api/upload/chunked/init`  
**Content-Type:** `application/json`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| filename | String | Yes | Name of the file |
| totalSize | Number | Yes | Total size of the file in bytes |
| mimeType | String | Yes | MIME type of the file |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/upload/chunked/init \
  -H "Content-Type: application/json" \
  -d '{"filename": "large_document.pdf", "totalSize": 15000000, "mimeType": "application/pdf"}'
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "upload_id": "550e8400-e29b-41d4-a716-446655440020",
    "chunk_size": 1048576
  }
}
```

**Endpoint:** `POST /api/upload/chunked/{upload_id}`  
**Content-Type:** `multipart/form-data`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| chunk | File | Yes | Chunk of the file |
| chunkIndex | Number | Yes | Zero-based index of the chunk |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/upload/chunked/550e8400-e29b-41d4-a716-446655440020 \
  -F "chunk=@chunk_data" \
  -F "chunkIndex=0"
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "received_chunks": 1,
    "total_received_size": 1048576
  }
}
```

**Endpoint:** `POST /api/upload/chunked/{upload_id}/complete`  
**Content-Type:** `application/json`

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/upload/chunked/550e8400-e29b-41d4-a716-446655440020/complete
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "file_id": "550e8400-e29b-41d4-a716-446655440030",
    "filename": "large_document.pdf",
    "file_size": 15000000,
    "mime_type": "application/pdf"
  }
}
```

### Generate Report

Generate a report from uploaded documents.

**Endpoint:** `POST /api/generate`  
**Content-Type:** `application/json`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| document_ids | Array | Yes | Array of document IDs to include in the report |
| additional_info | String | No | Additional instructions for the report |
| template_id | String | No | Template ID to use for the report |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "document_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "550e8400-e29b-41d4-a716-446655440001"
    ],
    "additional_info": "Include analysis of water damage in bathroom",
    "template_id": "550e8400-e29b-41d4-a716-446655440100"
  }'
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "report_id": "550e8400-e29b-41d4-a716-446655440200",
    "status": "processing"
  }
}
```

### Check Report Status

Check the status of a report generation request.

**Endpoint:** `GET /api/generate/status/{report_id}`

**Example Request:**
```bash
curl -X GET http://localhost:8000/api/generate/status/550e8400-e29b-41d4-a716-446655440200
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "report_id": "550e8400-e29b-41d4-a716-446655440200",
    "status": "completed",
    "progress": 100,
    "created_at": "2023-09-15T10:30:00Z",
    "completed_at": "2023-09-15T10:35:00Z"
  }
}
```

### Edit Report

Edit a generated report.

**Endpoint:** `POST /api/edit/{report_id}`  
**Content-Type:** `application/json`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| content | String | Yes | Updated content for the report |
| sections | Object | No | Changes to specific sections |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/edit/550e8400-e29b-41d4-a716-446655440200 \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Updated report content...",
    "sections": {
      "damage_assessment": "The water damage in the bathroom appears to be from..."
    }
  }'
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "report_id": "550e8400-e29b-41d4-a716-446655440200",
    "updated_at": "2023-09-15T11:00:00Z"
  }
}
```

### Refine Report

Request AI-powered refinement of a report.

**Endpoint:** `POST /api/edit/refine/{report_id}`  
**Content-Type:** `application/json`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| instructions | String | Yes | Instructions for the refinement |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/edit/refine/550e8400-e29b-41d4-a716-446655440200 \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": "Expand on the water damage section and add more detail about estimated repair costs."
  }'
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "report_id": "550e8400-e29b-41d4-a716-446655440200",
    "content": "The refined report content with expanded sections...",
    "updated_at": "2023-09-15T11:15:00Z"
  }
}
```

### Format Report

Format a report in different layouts.

**Endpoint:** `POST /api/format/{report_id}`  
**Content-Type:** `application/json`

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| format | String | Yes | Format type (e.g., "standard", "detailed", "summary") |
| options | Object | No | Additional formatting options |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/format/550e8400-e29b-41d4-a716-446655440200 \
  -H "Content-Type: application/json" \
  -d '{
    "format": "detailed",
    "options": {
      "include_images": true,
      "include_tables": true
    }
  }'
```

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "report_id": "550e8400-e29b-41d4-a716-446655440200",
    "formatted_id": "550e8400-e29b-41d4-a716-446655440300",
    "format": "detailed"
  }
}
```

### Download Report

Download a generated report.

**Endpoint:** `GET /api/download/{report_id}`

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| format | String | No | File format (pdf, docx, txt) - defaults to pdf |

**Example Request:**
```bash
curl -X GET http://localhost:8000/api/download/550e8400-e29b-41d4-a716-446655440200?format=docx \
  -O report.docx
```

**Success Response:**
The response will be the file content with appropriate Content-Type and Content-Disposition headers.

## Rate Limiting

The API implements rate limiting to prevent abuse:

- 100 requests per hour for most endpoints
- 25 requests per hour for resource-intensive endpoints (report generation, refinement)

Rate limit headers are included in responses:

```
X-Rate-Limit-Limit: 100
X-Rate-Limit-Remaining: 99
X-Rate-Limit-Reset: 3600
```

## WebSocket Events

Real-time updates are available via WebSocket connection:

**Connection URL:** `ws://localhost:8000/ws/{client_id}`

**Event Types:**

| Event | Description |
|-------|-------------|
| upload_progress | Progress updates for file uploads |
| report_progress | Progress updates for report generation |
| report_completed | Notification when a report is completed |
| error | Error notifications |

**Example WebSocket Message:**
```json
{
  "event": "report_progress",
  "data": {
    "report_id": "550e8400-e29b-41d4-a716-446655440200",
    "progress": 75,
    "status": "processing",
    "message": "Analyzing document 3 of 4"
  },
  "timestamp": "2023-09-15T11:30:00Z"
}
```

## Versioning

The API follows semantic versioning. The current version is v1.0.0. 