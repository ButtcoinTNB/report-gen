# Background Upload Implementation

## Overview

The background upload feature allows users to continue interacting with the application while files are being uploaded in the background. This implementation provides a seamless user experience by:

1. Starting uploads immediately upon file selection
2. Allowing users to proceed with additional information input while uploads continue
3. Providing real-time feedback on upload progress
4. Implementing robust error handling and retry mechanisms
5. Optimizing for performance with large files through chunked uploads

## Features

### Core Features

- **Immediate Upload Initiation**: Uploads begin as soon as files are selected
- **Visual Progress Indicators**: Real-time progress bars and file status indicators
- **Chunked Upload Support**: Large files are automatically split into manageable chunks
- **Error Recovery**: Failed uploads can be retried without restarting the entire process
- **Background Processing**: Users can continue using the application during uploads

### Enhanced Error Handling

- **Granular Error Categorization**: Errors are categorized by type (network, server, client, etc.)
- **Intelligent Retry Logic**: Automatic retries for transient errors with exponential backoff
- **User-Initiated Retries**: Interface for users to retry failed uploads
- **Detailed Error Messaging**: Clear explanations of what went wrong and how to fix it

## Implementation Details

### Component Structure

1. **FileUploader Component**
   - Primary interface for file selection and upload management
   - Displays upload progress and file status
   - Provides retry functionality for failed uploads

2. **ApiClient Class**
   - Enhanced with retry mechanisms and improved error handling
   - Categorizes errors and determines if they are retryable
   - Implements exponential backoff for retries

3. **UploadService**
   - Manages file uploads, including chunked uploads for large files
   - Calculates progress across multiple files

4. **Redux State Management**
   - `backgroundUpload` state tracks upload progress and status
   - Enables components to react to upload state changes

### Technical Implementation

#### FileUploader Component

The FileUploader component has been redesigned to support background uploads with retry functionality:

```jsx
// Key features in FileUploader.tsx
const FileUploader = ({ reportId, maxFiles, maxFileSize, acceptedFileTypes }) => {
  // State for tracking errors and retries
  const [uploadErrors, setUploadErrors] = useState([]);
  const [retrying, setRetrying] = useState(false);
  
  // Handle upload with retry logic
  const handleUpload = useCallback(async (files) => {
    // Upload process with progressive feedback
    // ...
  }, [/* dependencies */]);
  
  // Allow users to retry failed uploads
  const handleRetry = useCallback(async () => {
    // Retry logic for failed uploads
    // ...
  }, [/* dependencies */]);
  
  // Component UI with progress indicators and error handling
  return (
    <>
      {/* Upload interface */}
      {/* Error handling and retry UI */}
    </>
  );
};
```

#### ApiClient Error Handling

The ApiClient has been enhanced with sophisticated error handling:

```typescript
// Enhanced error handling in ApiClient.ts
export class ApiError extends Error {
  public readonly type: ApiErrorType;
  public readonly isRetryable: boolean;
  
  // Create ApiError from AxiosError with proper categorization
  static fromAxiosError(error: AxiosError): ApiError {
    // Determine error type and if it's retryable
    // ...
    
    return new ApiError(message, type, status, data, isRetryable);
  }
}

// Execute request with retry logic
private async executeRequest<T>(config, options): Promise<AxiosResponse<T>> {
  // Attempt request with configurable retry logic
  // ...
}
```

#### Redux State Management

```typescript
// Background upload state in reportSlice.ts
export interface BackgroundUploadState {
  isUploading: boolean;
  totalFiles: number;
  uploadedFiles: number;
  progress: number;
  error: string | null;
}

// Action to update background upload state
setBackgroundUpload: (state, action: PayloadAction<Partial<BackgroundUploadState>>) => {
  state.backgroundUpload = { ...state.backgroundUpload, ...action.payload };
}
```

### Upload Process Flow

1. **Initialization**
   - User selects files through drag-and-drop or file picker
   - `handleUpload` function is triggered with selected files
   - Upload state is initialized in Redux

2. **Processing Files**
   - Files are processed sequentially
   - Size validation is performed before upload attempts
   - Each file may be uploaded in chunks if it exceeds the size threshold

3. **Retry Mechanism**
   - Each file upload attempts up to MAX_RETRIES times with exponential backoff
   - Network and server errors are automatically retried
   - Client errors (except rate limiting) are not automatically retried

4. **Completion and Error Handling**
   - Successfully uploaded files update the documentIds in Redux
   - Failed uploads are tracked with detailed error information
   - Users can manually retry failed uploads

## Error Handling Strategy

### Error Categories

- **Network Errors**: Connection issues, timeouts
- **Server Errors**: 500-level errors
- **Client Errors**: 400-level errors
- **Authentication Errors**: 401, 403 errors
- **Unknown Errors**: Other error types

### Retry Strategy

- **Automatic Retries**: Network errors, timeouts, server errors, rate limiting (429)
- **Manual Retries**: User-initiated retries for any failed uploads
- **Exponential Backoff**: Increasing delay between retry attempts

### User Feedback

- **Progress Indicators**: File-level and overall progress bars
- **Status Indicators**: Visual cues for upload status (pending, uploading, complete, error)
- **Error Messages**: Clear, actionable error messages
- **Retry Options**: Interface elements for initiating retries

## Performance Optimization

### Chunked Uploads

Large files are automatically split into chunks (default 1MB) and uploaded sequentially:

1. Initialize chunked upload
2. Upload each chunk with progress tracking
3. Finalize upload when all chunks are complete

### Progress Calculation

Overall progress is calculated based on individual file progress and weighted by file size:

```javascript
// Example progress calculation
const updateProgress = (fileProgress, fileIndex, fileCount) => {
  const fileWeight = 1 / fileCount;
  const weightedProgress = fileProgress * fileWeight;
  totalProgress = (fileIndex * fileWeight * 100) + weightedProgress;
  onProgress(Math.floor(totalProgress));
};
```

## Testing

### Test Scenarios

- **Small File Upload**: Test normal upload flow with small files
- **Large File Upload**: Test chunked upload with files > threshold
- **Mixed File Upload**: Test batch of mixed-size files
- **Network Error Recovery**: Test automatic retry during network interruptions
- **Manual Retry**: Test user-initiated retry functionality
- **Concurrent Uploads**: Test performance with multiple simultaneous uploads

### Validation Points

- Progress updates correctly reflect actual upload progress
- Background upload continues when navigating to next step
- Failed uploads can be successfully retried
- Errors are properly displayed and categorized

## Browser Compatibility

- **Modern Browsers**: Full support in Chrome, Firefox, Safari, Edge
- **Older Browsers**: Basic functionality with fallbacks for missing features
- **Mobile Browsers**: Responsive design with touch-friendly controls

## Future Improvements

1. **Offline Support**: Queue uploads when offline and resume when connection is restored
2. **Upload Cancellation**: Allow users to cancel in-progress uploads
3. **Upload Analytics**: Track upload success rates and performance metrics
4. **Adaptive Chunk Size**: Dynamically adjust chunk size based on connection quality
5. **Upload Prioritization**: Allow important files to be prioritized in the upload queue

## Integration with Other Features

- **Report Generation**: Automatically triggers when background uploads complete
- **Additional Information**: Combines uploaded documents with user-provided context
- **Report Refinement**: Seamless transition to refinement after uploads complete

## Troubleshooting

### Common Issues

- **Upload Stalls**: Usually indicates a network issue or server timeout
- **Repeated Failures**: May indicate a file format issue or server configuration problem
- **Progress Reset**: Can occur if the session expires during a long upload

### Solutions

- **Retry Logic**: Most transient issues resolve with retry
- **File Validation**: Validate file types and sizes before upload begins
- **Network Monitoring**: Alert users to network issues affecting uploads
- **Session Management**: Extend session timeout during active uploads

## Conclusion

The background upload implementation significantly improves user experience by allowing continued interaction with the application during uploads. The robust error handling and retry mechanisms ensure reliability even in challenging network conditions. 