# API Specifications

This document details the API endpoints, request/response formats, and data structures used in the Insurance Report Generator application.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://report-gen-5wtl.onrender.com`

## Authentication

Most endpoints are protected by JWT authentication.

- **Headers**: Include `Authorization: Bearer {token}` in your requests

## API Endpoints Overview

The API is organized into the following categories:

1. **Upload**: Document upload endpoints
2. **Generate**: Report generation and analysis
3. **Format**: Document formatting
4. **Edit**: Report editing
5. **Download**: Report download

## Detailed Endpoint Specifications

### Upload

#### Upload Documents

```
POST /api/upload/documents
```

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `files`: Array of file objects
  - `template_id`: (Optional) Template ID for formatting

**Response:**
```json
{
  "report_id": 12345,
  "message": "Files uploaded successfully",
  "file_count": 2,
  "status": "success"
}
```

#### Upload Template

```
POST /api/upload/template
```

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `file`: PDF file to use as template

**Response:**
```json
{
  "template_id": 789,
  "message": "Template uploaded successfully",
  "status": "success"
}
```

### Generate

#### Analyze Documents

```
POST /api/generate/analyze
```

**Request:**
```json
{
  "document_ids": ["12345"],
  "additional_info": "Optional additional context"
}
```

**Response:**
```json
{
  "status": "success",
  "extracted_variables": {
    "customer_name": "John Smith",
    "policy_number": "POL-123456",
    "incident_date": "2023-01-15",
    "claim_amount": "5000.00"
  },
  "fields_needing_attention": ["customer_address", "policy_details"]
}
```

#### Generate Report

```
POST /api/generate/generate
```

**Request:**
```json
{
  "document_ids": ["12345"],
  "additional_info": "Additional context for the report generation"
}
```

**Response:**
```json
{
  "report_id": 67890,
  "preview_url": "https://example.com/preview/67890",
  "status": "success"
}
```

#### Refine Report

```
POST /api/generate/refine
```

**Request:**
```json
{
  "report_id": 67890,
  "instructions": "Please add more details about the incident location"
}
```

**Response:**
```json
{
  "report_id": 67891,
  "preview_url": "https://example.com/preview/67891",
  "status": "success"
}
```

### Format

#### Format as DOCX

```
POST /api/format/docx
```

**Request:**
```json
{
  "report_id": 67890,
  "template_id": 789
}
```

**Response:**
```json
{
  "docx_url": "https://example.com/documents/report_67890.docx",
  "status": "success"
}
```

### Download

#### Download Report

```
GET /api/download/{report_id}
```

**Query Parameters:**
- `format`: File format (pdf, docx) - Default: docx

**Response:**
- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document` or `application/pdf`
- File download

## Data Structures

### Report

```json
{
  "id": 67890,
  "user_id": 123,
  "title": "Insurance Claim Report",
  "content": "Full report content...",
  "created_at": "2023-04-15T14:30:00Z",
  "updated_at": "2023-04-15T15:45:00Z",
  "document_ids": [12345, 12346],
  "status": "completed"
}
```

### Document

```json
{
  "id": 12345,
  "user_id": 123,
  "filename": "claimant_statement.pdf",
  "file_path": "/uploads/user_123/claimant_statement.pdf",
  "file_type": "application/pdf",
  "file_size": 2048576,
  "created_at": "2023-04-15T14:15:00Z",
  "extracted_text": "Text content extracted from document..."
}
```

### User

```json
{
  "id": 123,
  "email": "user@example.com",
  "name": "John Smith",
  "created_at": "2023-01-10T09:00:00Z",
  "is_active": true
}
```

## Error Handling

All endpoints follow a consistent error response format:

```json
{
  "status": "error",
  "detail": "Detailed error message",
  "code": "ERROR_CODE"
}
```

Common error codes:

- `VALIDATION_ERROR`: Request validation failed
- `NOT_FOUND`: Resource not found
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Insufficient permissions
- `SERVER_ERROR`: Internal server error
- `AI_SERVICE_ERROR`: Error communicating with AI service

## Rate Limiting

- Default rate limit: 100 requests per hour per user
- Rate limit headers included in responses:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Time when the rate limit resets (Unix timestamp)

## Versioning

The API version is included in the response headers:

- `X-API-Version`: Current API version (e.g., "0.1.0") 