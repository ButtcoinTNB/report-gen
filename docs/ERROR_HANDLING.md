# Error Handling Guide

This document outlines the standard error handling patterns used throughout the Insurance Report Generator application to ensure consistent, informative, and user-friendly error responses.

## Table of Contents

1. [Backend Error Handling](#backend-error-handling)
   - [Standard Error Response Format](#standard-error-response-format)
   - [Using the Error Handler Decorator](#using-the-error-handler-decorator)
   - [Handling Specific Exceptions](#handling-specific-exceptions)
   - [Retry Operations](#retry-operations)
   
2. [Frontend Error Handling](#frontend-error-handling)
   - [Parsing Error Responses](#parsing-error-responses)
   - [Displaying Errors to Users](#displaying-errors-to-users)
   
3. [Logging Best Practices](#logging-best-practices)
   - [Log Levels](#log-levels)
   - [What to Log](#what-to-log)
   - [Development vs Production Logging](#development-vs-production-logging)

## Backend Error Handling

### Standard Error Response Format

All API errors follow this standard format:

```json
{
  "status": "error",
  "error_type": "validation_error",
  "message": "User-friendly error message",
  "operation": "Description of the operation that failed"
}
```

In development mode, an additional field `traceback` may be included.

### Using the Error Handler Decorator

For FastAPI endpoints, use the `api_error_handler` decorator:

```python
from utils.error_handler import api_error_handler

@router.post("/endpoint")
@api_error_handler  # Always place after the FastAPI router decorator
async def my_endpoint():
    # Function code here
    pass
```

This decorator automatically catches exceptions and returns standardized error responses.

### Handling Specific Exceptions

For fine-grained control, use the `handle_exception` function:

```python
from utils.error_handler import handle_exception

try:
    # Your code here
except ValueError as e:
    handle_exception(e, "validating user input", default_status_code=400)
except FileNotFoundError as e:
    handle_exception(e, "retrieving file", default_status_code=404)
```

Common error types mapped to status codes:
- `ValidationError`: 422 (Unprocessable Entity)
- `ValueError`: 400 (Bad Request)
- `KeyError`: 400 (Bad Request)
- `FileNotFoundError`: 404 (Not Found)
- `PermissionError`: 403 (Forbidden)
- `NotImplementedError`: 501 (Not Implemented)
- `TimeoutError`: 504 (Gateway Timeout)
- `ConnectionError`: 503 (Service Unavailable)

### Retry Operations

For operations that might fail temporarily (e.g., network calls), use the retry utility:

```python
from utils.error_handler import retry_operation

def my_operation():
    # Code that might fail temporarily

result = retry_operation(
    my_operation,
    max_retries=3,
    operation_name="fetching external data",
    retry_exceptions=(ConnectionError, TimeoutError)
)
```

## Frontend Error Handling

### Parsing Error Responses

Use the `formatApiError` and `handleApiError` functions from `utils/errorHandler.js`:

```javascript
import { handleApiError } from "../utils/errorHandler";

try {
  const response = await api.someRequest();
  return response.data;
} catch (error) {
  return handleApiError(error, "operation description");
}
```

### Displaying Errors to Users

For UI components, use the formatted error messages:

```javascript
import { formatApiError } from "../utils/errorHandler";

// In a component's error handler
const errorMessage = formatApiError(error);
setErrorState(errorMessage);
```

The frontend error handler will automatically parse the standardized backend error format and display appropriate messages.

## Logging Best Practices

### Log Levels

Use appropriate log levels:

- `logger.debug`: Detailed information for debugging
- `logger.info`: Confirmation that things are working as expected
- `logger.warning`: Something unexpected happened, but the application can continue
- `logger.error`: Something failed, but the application can recover
- `logger.critical`: The application cannot continue

### What to Log

1. **Context**: Always include operation context in logs
2. **Input validation**: Log invalid inputs (without sensitive data)
3. **Exceptions**: Log full exception details including stack traces
4. **State changes**: Log important application state changes
5. **Performance**: Log timing for slow operations

### Development vs Production Logging

- **Development**: Verbose logging with stack traces
- **Production**: Concise, actionable messages without sensitive data

In production, use the `include_traceback=False` parameter with `handle_exception` to avoid exposing sensitive stack traces.

## Examples

### Complete Backend Example

```python
from fastapi import APIRouter
from utils.error_handler import api_error_handler, handle_exception, logger

router = APIRouter()

@router.post("/documents")
@api_error_handler
async def upload_documents(files):
    # This will automatically handle exceptions
    # and return standardized error responses
    
    if not files:
        handle_exception(
            ValueError("No files provided"),
            "validating upload request",
            default_status_code=400
        )
    
    logger.info(f"Processing {len(files)} files")
    
    # Rest of the function...
```

### Complete Frontend Example

```javascript
import axios from "axios";
import { handleApiError } from "../utils/errorHandler";

export async function uploadFile(files) {
  try {
    const formData = new FormData();
    
    // Add files to form data
    files.forEach(file => formData.append("files", file));
    
    // Log request details
    console.log(`Uploading ${files.length} files`);
    
    const response = await axios.post("/api/upload/documents", formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    
    return response.data;
  } catch (error) {
    // This will log details, format the error message,
    // and throw a new error with the formatted message
    return handleApiError(error, "file upload");
  }
}
``` 