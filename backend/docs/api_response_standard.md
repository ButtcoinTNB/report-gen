# Standardized API Response Format

To ensure consistency across all API endpoints, the Insurance Report Generator now uses a standardized response format. This document explains the structure and how to use it in your API endpoints.

## Response Structure

All API responses follow this standard format:

```json
{
  "status": "success|error",
  "data": { ... },
  "message": "Human-readable message",
  "code": "MACHINE_READABLE_CODE"
}
```

### Fields

- **status**: Always either "success" or "error"
- **data**: The response payload (null for error responses)
- **message**: A human-readable message (optional for success responses)
- **code**: A machine-readable error/success code (optional for success responses)

## Using the Standardized Format

### In Route Handlers

Use the `APIResponse` model in your route handlers:

```python
from api.schemas import APIResponse

@router.get("/items/{item_id}", response_model=APIResponse[ItemSchema])
async def get_item(item_id: int):
    item = await fetch_item(item_id)
    if not item:
        return APIResponse(
            status="error",
            message="Item not found",
            code="ITEM_NOT_FOUND"
        )
    return APIResponse(
        status="success",
        data=item,
        message="Item retrieved successfully"
    )
```

### Automatic Error Handling

Use the `api_error_handler` decorator to automatically wrap responses and catch exceptions:

```python
from utils.error_handler import api_error_handler

@router.get("/users")
@api_error_handler
async def get_users():
    # This will automatically be wrapped in APIResponse
    return {"users": await fetch_users()}
```

## Common Error Codes

| Code | Description |
| --- | --- |
| VALIDATION_ERROR | Invalid request data |
| NOT_FOUND | Resource not found |
| UNAUTHORIZED | Authentication required |
| FORBIDDEN | Permission denied |
| INTERNAL_ERROR | Server error |
| AI_SERVICE_ERROR | Error in AI processing |
| FILE_TOO_LARGE | Uploaded file exceeds size limit |

## Frontend Integration

When working with these responses in the frontend, always check the `status` field first:

```typescript
// TypeScript example
interface APIResponse<T> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
  code?: string;
}

async function fetchData<T>(url: string): Promise<T> {
  const response = await fetch(url);
  const result = await response.json() as APIResponse<T>;
  
  if (result.status === 'error') {
    throw new Error(`${result.message} (${result.code})`);
  }
  
  return result.data as T;
}
``` 