# File Handling Enhancements

## Overview

We've enhanced the file handling capabilities of the Insurance Report Generator by implementing a comprehensive `FileProcessor` class with support for chunked file uploads. This enables efficient handling of large files and reduces code duplication across the application.

## Key Improvements

1. **Enhanced FileProcessor Class**
   - Centralized file operations for consistent handling
   - Comprehensive MIME type detection
   - Safe path handling to prevent traversal attacks
   - Text and image extraction utilities

2. **Chunked Upload Support**
   - Breaking large files into manageable chunks for upload
   - Progress tracking for uploads
   - Efficient handling of files of any size
   - Persistent tracking of upload state

3. **API Endpoint Updates**
   - New RESTful endpoints for chunked uploads
   - Standardized error handling
   - Detailed progress reporting

4. **Testing**
   - Comprehensive test cases for chunked uploads
   - Full flow verification from initialization to completion

## Implementation Details

The chunked upload flow works as follows:

1. Client initializes upload, providing total file size and number of chunks
2. Server returns upload ID and tracking information
3. Client uploads each chunk sequentially with the chunk index
4. Server saves chunks and updates tracking information
5. After all chunks are uploaded, client requests completion
6. Server combines chunks into the final file, processes it, and cleans up

## Testing

To test the chunked upload functionality:

### Manual Testing

Use the API endpoints directly with tools like curl or Postman:

```bash
# Initialize upload
curl -X POST "http://localhost:8000/api/upload/chunked/init" \
  -H "Content-Type: application/json" \
  -d '{"filename":"large_file.pdf","fileSize":5000000,"fileType":"application/pdf","totalChunks":10}'

# Upload a chunk (repeat for each chunk)
curl -X POST "http://localhost:8000/api/upload/chunked/chunk/{upload_id}/{chunk_index}" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@chunk_data"

# Complete upload
curl -X POST "http://localhost:8000/api/upload/chunked/complete" \
  -H "Content-Type: application/json" \
  -d '{"uploadId":"{upload_id}"}'

# Check status
curl "http://localhost:8000/api/upload/chunked/status/{upload_id}"
```

### Automated Testing

The automated tests are in `backend/tests/test_chunked_upload.py` and verify:

- Initialization of chunked uploads
- Saving individual chunks
- Completing uploads
- Status tracking
- Error handling

## Example Frontend Integration

Here's how you might use this in a React frontend:

```javascript
// Initialize upload
const initUpload = async (file) => {
  const chunkSize = 1024 * 1024; // 1MB chunks
  const totalChunks = Math.ceil(file.size / chunkSize);
  
  const response = await fetch('/api/uploads/initialize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filename: file.name,
      fileSize: file.size,
      fileType: file.type,
      totalChunks
    })
  });
  
  const { data } = await response.json();
  return { uploadId: data.uploadId, totalChunks };
};

// Upload chunks
const uploadChunks = async (file, uploadId, totalChunks, onProgress) => {
  const chunkSize = 1024 * 1024; // 1MB chunks
  
  for (let i = 0; i < totalChunks; i++) {
    const start = i * chunkSize;
    const end = Math.min(start + chunkSize, file.size);
    const chunk = file.slice(start, end);
    
    const formData = new FormData();
    formData.append('file', chunk);
    
    await fetch(`/api/upload/chunked/chunk/${uploadId}/${i}`, {
      method: 'POST',
      body: formData
    });
    
    onProgress((i + 1) / totalChunks * 100);
  }
};

// Complete upload
const completeUpload = async (uploadId) => {
  const response = await fetch('/api/upload/chunked/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uploadId })
  });
  
  return await response.json();
};
```

## Next Steps

1. Add database-backed tracking for better persistence
2. Implement WebSocket-based progress events
3. Add support for resumable uploads
4. Integrate with cloud storage providers 