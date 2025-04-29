# Chunked File Upload Implementation

This document provides a comprehensive overview of the chunked file upload implementation in the Insurance Report Generator application.

## Purpose

The chunked upload feature allows the system to handle large files efficiently by:

1. Breaking large files into smaller, manageable chunks
2. Uploading each chunk separately
3. Reassembling the chunks on the server
4. Verifying the integrity of the combined file

This approach offers several advantages:

- **Reliability**: Reduced chance of upload failures for large files
- **Resumability**: Ability to resume interrupted uploads
- **Progress Tracking**: More accurate progress reporting
- **Reduced Memory Usage**: Lower memory pressure on both client and server
- **Improved User Experience**: Users can upload files of any size

## Implementation Details

### Backend (Python/FastAPI)

The backend implementation is managed by the `FileProcessor` class, which handles:

1. **Initialization**: Creating a temporary directory and metadata for the chunked upload
2. **Chunk Processing**: Receiving and storing individual chunks
3. **Completion**: Combining chunks into the final file and verifying integrity
4. **Cleanup**: Removing temporary files and directories

#### API Endpoints

The implementation exposes three main API endpoints:

1. **`/api/uploads/initialize`**: Initializes a chunked upload session
   - Input: Filename, file size, total chunks, MIME type
   - Output: Upload ID, status information
   
2. **`/api/upload/chunked/chunk/{upload_id}/{chunk_index}`**: Handles individual chunk uploads
   - Input: Chunk data, upload ID, chunk index
   - Output: Confirmation of chunk receipt, status information
   
3. **`/api/upload/chunked/complete`**: Finalizes the upload
   - Input: Upload ID
   - Output: Final file information, including file ID, path, size, and MIME type

#### Data Storage

Chunks are stored in a temporary directory structure:
```
/tmp/chunked_uploads/
  └── {upload_id}/
      ├── metadata.json  # Contains file information and status
      ├── chunk_0        # First chunk
      ├── chunk_1        # Second chunk
      └── ...            # Additional chunks
```

### Frontend (JavaScript/TypeScript)

The frontend implementation is primarily contained in:

1. **`UploadService.ts`**: Handles the chunked upload logic
2. **`FileUpload.tsx`**: Provides the user interface

#### Upload Process

The frontend implementation follows these steps:

1. **File Selection**: User selects files via drag-and-drop or file browser
2. **Size Detection**: Files larger than `CHUNKED_UPLOAD_SIZE_THRESHOLD` (50MB) are processed as chunked uploads
3. **Initialization**: Backend provides an upload ID
4. **Chunk Processing**:
   - File is sliced into chunks (5MB by default)
   - Chunks are uploaded sequentially with progress tracking
   - Retry logic handles any failed uploads
5. **Completion**: Backend combines chunks into the final file

#### Progress Tracking

The implementation provides detailed progress tracking:
- Overall progress across all files
- Individual file progress
- Chunked upload progress at the chunk level

## Configuration Options

### Backend Configuration

- `UPLOAD_CHUNK_SIZE`: Maximum chunk size (default: 5MB)
- `TEMP_DIR`: Directory for temporary storage (default: system temp directory)
- `CLEANUP_INTERVAL`: How often to clean up abandoned uploads (default: 24 hours)

### Frontend Configuration

- `CHUNKED_UPLOAD_SIZE_THRESHOLD`: File size threshold for chunked upload (default: 50MB)
- `DEFAULT_CHUNK_SIZE`: Size of each chunk (default: 5MB)
- `MAX_RETRIES`: Maximum retry attempts for failed chunk uploads (default: 3)
- `RETRY_DELAY`: Delay between retry attempts (default: 2000ms)

## Testing

### Automated Testing

1. **Backend Tests**: Unit and integration tests for the chunked upload functionality
   - Run with: `cd backend && python -m pytest tests/test_chunked_upload.py -v`

2. **Frontend Test Script**: Simulates a chunked upload with a large test file
   - Run with: `cd frontend && npm run test-chunked-upload`

### Manual Testing

1. Start the application (both backend and frontend)
2. Upload files larger than 50MB through the UI
3. Monitor progress and verify successful upload

## Error Handling

The implementation includes robust error handling:

1. **Network Failures**: Automatic retry mechanism for failed chunk uploads
2. **Server Errors**: Detailed error responses with appropriate HTTP status codes
3. **Client-Side Validation**: Verification of file types and sizes
4. **Timeout Handling**: Configurable timeouts for API requests

## Security Considerations

1. **Temporary File Cleanup**: Automatic cleanup of temporary files
2. **File Type Validation**: MIME type checking before and after upload
3. **Upload Size Limits**: Configurable limits for maximum file size
4. **Path Traversal Prevention**: Safe path handling for all file operations

## Future Enhancements

1. **Parallel Uploads**: Upload multiple chunks concurrently for faster uploads
2. **Resumable Uploads**: Ability to resume uploads after browser refresh or application restart
3. **Chunk Compression**: Compress chunks before upload to reduce bandwidth usage
4. **Client-Side Hashing**: Generate file hashes on the client for integrity verification 