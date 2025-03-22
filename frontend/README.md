# Insurance Report Generator Frontend

A modern, React-based frontend application for generating insurance reports from uploaded documents with sophisticated background processing capabilities.

## Features

- **Seamless File Uploads**: Upload insurance documents with real-time progress tracking
- **Background Processing**: Continue using the application while files upload in the background
- **Error Recovery**: Robust error handling with automatic and manual retry mechanisms
- **Multi-step Workflow**: Guided process from document upload to report refinement
- **AI-powered Report Generation**: Automatic generation of comprehensive insurance reports
- **Report Refinement**: Interactive editing and improvement of generated reports

## Technical Overview

### Core Technologies

- **React**: Frontend framework
- **TypeScript**: Type-safe JavaScript
- **Material UI**: Component library for consistent UI
- **Redux**: State management
- **Axios**: Enhanced API client with retry mechanisms

### Key Components

- **FileUploader**: Primary interface for file uploads with background processing
- **ReportGenerator**: Controls the report generation process
- **DocxPreviewEditor**: Allows viewing and refinement of generated reports
- **JourneyVisualizer**: Visualizes the user's progress through the application
- **ReportStepper**: Orchestrates the multi-step workflow

## Background Upload Implementation

The background upload feature allows users to continue interacting with the application while files are being uploaded. This significantly improves user experience, especially when dealing with large documents.

### Key Design Points

1. **Immediate Upload Initiation**: Uploads begin as soon as files are selected
2. **Real-time Progress Tracking**: Visual feedback on upload status
3. **Error Recovery**: Automatic retries with exponential backoff for transient errors
4. **Manual Retry Options**: User-initiated retries for failed uploads
5. **Performance Optimization**: Chunked uploads for large files

See [BACKGROUND_UPLOAD.md](./docs/BACKGROUND_UPLOAD.md) for detailed documentation.

## Error Handling Strategy

The application implements a sophisticated error handling approach:

1. **Error Categorization**: Errors are categorized by type (network, server, client, etc.)
2. **Intelligent Retry Logic**: Automatic retries for transient errors
3. **User Feedback**: Clear, actionable error messages
4. **Exponential Backoff**: Increasing delays between retries to prevent overwhelming the server

### Error Categories

- **Network Errors**: Connection issues, timeouts
- **Server Errors**: 500-level errors
- **Client Errors**: 400-level errors
- **Authentication Errors**: 401, 403 errors
- **Unknown Errors**: Other error types

### ApiClient Enhancements

The application uses an enhanced ApiClient with improved error handling:

```typescript
export class ApiError extends Error {
  public readonly type: ApiErrorType;
  public readonly isRetryable: boolean;
  
  // Determines if an error should be automatically retried
  static fromAxiosError(error: AxiosError): ApiError {
    // Categorize error and determine if it's retryable
    // ...
  }
}
```

## Performance Optimizations

The application includes several performance optimizations:

1. **Lazy Loading**: Heavy components are loaded only when needed
2. **Chunked Uploads**: Large files are split into manageable chunks
3. **Debounced Actions**: User interactions are debounced to prevent excessive re-renders
4. **Memoization**: Expensive calculations and renders are memoized

### Lazy Loading Implementation

```typescript
// Lazy loaded components
export const DocxPreviewEditor = lazy(() => 
  import('./DocxPreviewEditor').then(module => ({ 
    default: module.DocxPreviewEditor 
  }))
);
```

## Project Structure

```
frontend/
├── components/       # React components
├── services/         # API services and data management
│   └── api/          # API clients and interfaces
├── store/            # Redux state management
├── types/            # TypeScript type definitions
├── utils/            # Utility functions
└── docs/             # Documentation
    └── BACKGROUND_UPLOAD.md   # Detailed background upload documentation
```

## Getting Started

1. **Installation**:
   ```bash
   npm install
   ```

2. **Development**:
   ```bash
   npm run dev
   ```

3. **Build**:
   ```bash
   npm run build
   ```

## Testing

The application includes comprehensive tests for critical functionality:

```bash
# Run all tests
npm test

# Test specific component
npm test -- -t "FileUploader"
```

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a pull request

## License

This project is proprietary and confidential. Unauthorized copying or distribution is prohibited.
