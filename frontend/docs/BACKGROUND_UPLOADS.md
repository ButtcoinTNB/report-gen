# Background File Upload

This document explains the background file upload feature in the Insurance Report Generator application.

## Overview

The background upload feature allows users to continue interacting with the application while their files are being uploaded in the background. This improves the user experience by:

1. Reducing perceived wait time
2. Allowing users to input additional information while uploads progress
3. Supporting large files through chunked uploads
4. Providing real-time progress feedback

## How to Use

1. Simply drag & drop files or select them through the file browser
2. Once you initiate the upload, you'll immediately proceed to the next step
3. A progress indicator will show the status of your background upload
4. You can provide additional information while your files upload
5. The "Generate Report" button will be disabled until uploads complete

## Technical Implementation

### Frontend Components

- **FileUploader**: Handles file selection and initiates background upload
- **AdditionalInfoInput**: Allows users to provide context while uploads progress
- **ReportGenerator**: Shows upload status and manages the "Generate" button state

### State Management

The upload state is tracked in Redux with the following fields:

```typescript
interface BackgroundUploadState {
  isUploading: boolean;
  totalFiles?: number;
  uploadedFiles?: number;
  progress: number;
  error?: string | null;
}
```

### Upload Process

1. Files are selected via the FileUploader component
2. Upload begins immediately and the user proceeds to the next step
3. Upload status is tracked in Redux state
4. The UI updates progressively as files upload
5. Once complete, document IDs are stored for report generation

### Large File Support

Files larger than 50MB are automatically processed using chunked uploads:

1. File is split into 5MB chunks
2. Each chunk is uploaded separately
3. Server reassembles the chunks
4. Progress is reported accurately for each chunk

## Performance Considerations

- Upload requests happen in parallel for small files
- Large files use sequential chunk uploads with progress tracking
- Uploads are handled by a dedicated background thread on the server
- Temporary files are automatically cleaned up after processing

## Limitations

- Maximum supported file size: 100MB per file
- Maximum number of files per upload: 20
- Supported file types: PDF, DOCX, DOC, TXT, XLS, XLSX, CSV, Images

## Error Handling

If an upload fails:

1. An error message is displayed
2. The user can retry the failed upload
3. Partially uploaded files are cleaned up automatically

## Testing

The implementation has been thoroughly tested with:

- Small files (< 5MB)
- Large files (> 50MB)
- Multiple simultaneous uploads
- Various connection speeds and conditions

## Browser Compatibility

This feature is compatible with all modern browsers:
- Chrome 50+
- Firefox 55+
- Safari 10+
- Edge 18+

## Future Improvements

Planned enhancements include:
- Resumable uploads for connection failures
- Background processing notifications
- Upload pause/resume functionality
- Enhanced error recovery 