# File Handling Utilities

This document provides an overview of the file handling utilities in the Insurance Report Generator application, including the enhancements made to reduce code duplication and improve large file handling.

## FileProcessor Class

The `FileProcessor` class in `backend/utils/file_processor.py` serves as a centralized utility for all file-related operations. This helps reduce code duplication and ensures consistent file handling across the application.

### Key Features

- **Comprehensive MIME type detection** - Reliable file type detection using multiple methods
- **Standardized file information** - Consistent file metadata format across the application
- **Text and image processing** - Utilities for handling different types of files
- **Safe path handling** - Prevention of path traversal attacks
- **Chunked file uploads** - Support for large file uploads in multiple chunks

### Basic Usage Examples

```python
# Get file information
file_info = FileProcessor.get_file_info("path/to/file.pdf")

# Extract text from a document
text = FileProcessor.extract_text("path/to/document.pdf")

# Save an uploaded file safely
file_data = FileProcessor.save_upload(uploaded_file, "uploads/dir")

# Get a file as base64 for embedding
base64_data = FileProcessor.get_file_as_base64("path/to/image.jpg")

# Use safe path joining to prevent traversal attacks
safe_path = FileProcessor.safe_path_join(base_dir, user_provided_filename)
```

## Chunked File Upload Support

The enhanced `FileProcessor` now includes support for chunked file uploads, which is essential for handling large files efficiently, particularly in web applications.

### Chunked Upload Flow

1. **Initialize Upload**: Create metadata for a new chunked upload
   ```python
   upload_info = FileProcessor.init_chunked_upload(
       upload_id="unique-id",
       filename="large_file.pdf",
       total_chunks=10,
       file_size=50000000,  # 50MB
       mime_type="application/pdf",
       directory="uploads/dir"
   )
   ```

2. **Upload Chunks**: Send and save individual chunks
   ```python
   for i, chunk_data in enumerate(chunks):
       chunk_info = FileProcessor.save_chunk(
           upload_id="unique-id",
           chunk_index=i,
           chunk_data=chunk_file_object
       )
   ```

3. **Complete Upload**: Combine all chunks into the final file
   ```python
   result = FileProcessor.complete_chunked_upload(
       upload_id="unique-id",
       target_directory="uploads/dir"
   )
   ```

4. **Track Progress**: Check status of an ongoing upload
   ```python
   status = FileProcessor.get_chunked_upload_status("unique-id")
   progress = (status["received_chunks"] / status["total_chunks"]) * 100
   ```

5. **Cleanup**: Remove temporary chunks and metadata
   ```python
   FileProcessor.cleanup_chunked_upload("unique-id")
   ```

### API Endpoints for Chunked Uploads

The application provides RESTful API endpoints for chunked uploads:

- `POST /api/upload/chunked/init` - Initialize a new chunked upload
- `POST /api/upload/chunked/chunk/{upload_id}/{chunk_index}` - Upload a single chunk
- `POST /api/upload/chunked/complete` - Complete a chunked upload
- `GET /api/upload/chunked/status/{upload_id}` - Get upload status

## Benefits of the Enhanced File Handling

1. **Reduced Code Duplication**: Common file operations are centralized in one utility class
2. **Consistent Error Handling**: Standardized approaches to file-related errors
3. **Improved Security**: Safe path handling prevents path traversal attacks
4. **Support for Large Files**: Chunked uploads enable handling files of any size
5. **Simplified Testing**: Centralized utilities are easier to test and maintain
6. **Better Developer Experience**: Clear, well-documented APIs for file operations

## Implementation Details

The `FileProcessor` uses several techniques to ensure robust file handling:

- **Multiple MIME Detection Methods**: Falls back to extension-based detection if magic fails
- **Persistent Tracking**: Maintains upload state even if server restarts
- **Error Resilience**: Detailed error handling and validation
- **Cleanup Management**: Temporary files are properly managed
- **Progress Tracking**: Detailed status tracking for long-running operations

## Future Improvements

Potential enhancements for the file handling system:

1. **Database-backed upload tracking**: Replace in-memory tracking with database storage
2. **Progress Events**: WebSocket-based progress events for real-time updates
3. **Resumable Uploads**: Allow uploads to be paused and resumed
4. **Intelligent Chunk Sizing**: Adapt chunk size based on network conditions
5. **Virus Scanning**: Integrate with virus scanning services
6. **Cloud Storage Integration**: Direct uploads to cloud storage providers 