# Insurance Report Generator

An AI-powered system that generates professional insurance reports from various document types. The system uses a dual-agent approach with a writer and reviewer to ensure high-quality, consistent reports following company guidelines.

## Authentication & Access

This is a public API service - no authentication is required to use the core features. The system uses rate limiting for protection against abuse. While authentication is supported, it is entirely optional and only used for:
- Associating uploaded files with user accounts (if desired)
- Better tracking and management of reports
- Future features that may require user context

Users can freely:
- Upload documents
- Generate reports
- Download reports
- All other core functionality

Rate limiting is applied to prevent abuse:
- 100 requests per hour for most endpoints
- 25 requests per hour for resource-intensive endpoints

## Features

- **Multi-format Document Support**:
  - Documents: PDF, DOC, DOCX, RTF, ODT, TXT, CSV, MD, HTML
  - Spreadsheets: XLS, XLSX
  - Images: JPG, JPEG, PNG, GIF, BMP, WEBP, TIFF
  - OCR support for text extraction from images
  - Excel data extraction with sheet preservation

- **AI Agent Loop**:
  - Writer Agent: Generates initial report drafts
  - Reviewer Agent: Evaluates and provides feedback
  - Iterative improvement process
  - Quality scoring system
  - Automatic formatting according to brand guidelines

- **Modern UI/UX**:
  - Real-time progress tracking
  - Live preview of generated reports
  - Interactive feedback display
  - Document upload with drag-and-drop
  - DOCX export functionality

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/insurance-report-generator.git
   cd insurance-report-generator
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env.local
   ```
   Edit `.env.local` with your API keys and configuration.

## Development

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

## File Processing

The system supports various file formats through specialized processors:

- **Documents**: Uses `mammoth` for DOCX, native text processing for TXT/CSV/etc.
- **PDFs**: Utilizes `pdfjs-dist` for text extraction
- **Images**: Implements `tesseract.js` for OCR in Italian and English
- **Excel**: Processes spreadsheets using `xlsx` with sheet preservation

## AI Agent Loop

The system implements a dual-agent approach for report generation:

1. **Writer Agent**:
   - Analyzes input documents
   - Extracts relevant information
   - Generates initial report draft
   - Follows brand guidelines and formatting rules

2. **Reviewer Agent**:
   - Evaluates report quality
   - Checks compliance with guidelines
   - Provides specific improvement suggestions
   - Assigns quality score

3. **Iteration Process**:
   - Maximum 3 iterations
   - Continues until quality threshold is met (90% score)
   - Each iteration improves based on reviewer feedback
   - Final report includes quality score and suggestions

## API Routes

### POST /api/agent-loop

Handles document processing and report generation:

```typescript
interface AgentLoopResponse {
  draft: string;
  feedback: {
    score: number;
    suggestions: string[];
  };
  downloadUrl: string;
  iterations: number;
}
```

## Error Handling

The system implements comprehensive error handling:

- File validation and MIME type checking
- Graceful fallbacks for unsupported formats
- Detailed error messages for debugging
- User-friendly error displays
- Automatic retry mechanisms for OCR

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# Agent Loop Initialization System

This implementation provides a robust system for initializing and tracking the AI agent loop process for report generation. It has been designed to be simple, efficient, elegant, and non-disruptive to the existing codebase.

## Features

### API Integration (Plan 3, point 2.1)

- **Robust API Client**: Enhanced `ReportService` with a specialized `initializeAgentLoop` method that includes error handling, request validation, retry logic, and response processing.
- **Task Status Polling**: Implemented a polling mechanism for long-running agent tasks, with proper timeout handling.
- **Request Queue Management**: Created a task management system in the backend with status tracking and event notifications.
- **Report ID Validation**: Added validation to ensure report IDs are correctly associated with uploaded files.
- **Recovery Mechanisms**: Implemented error detection and automatic retry with exponential backoff for transient failures.

### User Feedback During Initialization (Plan 3, point 2.2)

- **Progress Tracking**: Created an elegant `AgentInitializationTracker` component that shows real-time progress updates during initialization.
- **Estimated Time**: Dynamic calculation and display of estimated completion time based on current progress.
- **Cancellation Options**: Implemented a cancellation system that allows users to safely abort ongoing operations.
- **Error Handling**: Enhanced error display with clear guidance on how to resolve issues.
- **Detailed Information**: Added expandable technical details for advanced users or troubleshooting.

## Implementation Details

### Frontend

- **State Management**: Extended Redux store with a dedicated `agentLoop` state for tracking initialization progress.
- **Components**: Created modular components for tracking agent initialization status with both compact and full display options.
- **Service Layer**: Enhanced API service with robust error handling and retry logic.

### Backend

- **Task Management**: Implemented a task management system for handling long-running agent processes.
- **Cancelation Support**: Added API endpoint for cancelling ongoing tasks.
- **Event System**: Created a server-sent events (SSE) system for real-time status updates.

## Usage

The agent initialization system is designed to be used as follows:

```typescript
// Initialize Redux state
dispatch(initAgentLoop());

// Start agent loop with progress tracking
const result = await reportService.initializeAgentLoop(
  {
    reportId: "your-report-id",
    additionalInfo: "Additional information for the report"
  },
  (progress, message) => {
    // Update UI with progress and message
    dispatch(updateAgentLoopProgress({ progress, message }));
  }
);

// Handle completion
dispatch(completeAgentLoop({
  content: result.draft,
  previewUrl: result.docxUrl,
  iterations: result.iterations
}));
```

To display the progress tracker in your components:

```tsx
<AgentInitializationTracker 
  variant="full"  // or "compact" for a minimal version
  showDetails={false}  // whether to show expanded details by default
/>
```

## Error Handling

The system includes comprehensive error handling with:

- Automatic retries with exponential backoff
- User-friendly error messages
- Cancellation mechanisms
- Session timeout handling

## Future Improvements

Potential future enhancements could include:

- WebSocket-based real-time updates instead of polling
- More accurate time estimation based on document size and complexity
- Enhanced progress visualization with document-specific status

# Recent Improvements

The Agent Loop Initialization System has undergone several important improvements:

## 1. Configuration and Flexibility

- Added a centralized configuration system (`apiConfig`) for all API-related settings
- Made polling intervals, timeouts, retry logic, and other parameters configurable
- Ensured hardcoded values are replaced with configurable parameters throughout the codebase

## 2. WebSocket Implementation

- Implemented WebSocket support for real-time task status updates
- Created a fallback mechanism to polling when WebSockets are unavailable
- Added robust reconnection logic with exponential backoff
- Ensured proper cleanup of WebSocket connections to prevent resource leaks

## 3. Error Recovery Enhancements

- Improved network error detection and recovery
- Added automatic retry mechanisms for transient failures
- Implemented detailed error categorization with specific user guidance
- Enhanced error display with recovery suggestions based on error type

## 4. Security Improvements

- Added user validation for sensitive operations like task cancellation
- Implemented JWT-based authentication support
- Created role-based access control for administrative functions
- Added protection against unauthorized task cancellation

## 5. Resource Management

- Fixed memory leaks in component cleanup
- Implemented proper resource tracking and cleanup for backend processes
- Added graceful termination of tasks during cancellation
- Enhanced connection management to prevent orphaned connections

## 6. Import/Export Standardization

- Fixed import/export inconsistencies between components
- Standardized how components are imported from index files
- Ensured proper module resolution throughout the application

These improvements make the Agent Loop Initialization System more robust, efficient, and maintainable while preserving the core functionality and user experience.

# Insurance Report Generator - System Improvements

This document outlines recent improvements made to the Insurance Report Generator application to enhance robustness, efficiency, and maintainability.

## Recent System Enhancements

### 1. Transaction-Based State Management

The frontend state management has been enhanced with transaction-based patterns to prevent race conditions and ensure data consistency during critical operations:

- **Transaction Tracking**: Redux state now tracks pending transactions with their status and metadata.
- **Atomic Operations**: Critical state changes (like cancellations and reconnections) are managed as atomic transactions.
- **Cleanup Mechanism**: Stale transactions are automatically cleaned up after 5 minutes.
- **Race Condition Prevention**: State updates are only applied if they belong to the current transaction or if no transaction is in progress.

**Key files:**
- `frontend/src/store/reportSlice.ts` - Transaction state management
- `frontend/src/services/api/ReportService.ts` - Transaction implementation in API service

### 2. Standardized Error Handling

A comprehensive error handling system has been implemented to standardize error responses and improve troubleshooting:

- **Centralized Error Handler**: Common error handling logic with standardized error types and responses.
- **Error Categorization**: Errors are categorized by type (authentication, validation, not found, etc.) with appropriate HTTP status codes.
- **Structured Error Responses**: All errors follow a consistent format with status, code, message and contextual details.
- **Transaction Tracing**: Error responses include transaction IDs for cross-component tracing.
- **Retryable Errors**: Flags indicating whether operations can be retried automatically.

**Key files:**
- `backend/utils/error_handler.py` - Centralized error handling utilities

### 3. Resource Management and Cleanup

Improved resource management systems ensure proper initialization, tracking, and cleanup of system resources:

- **Dependency Manager**: Centralized tracking of system dependencies and resources.
- **Resource Trackers**: Type-safe resource tracking with automatic cleanup.
- **Connection Management**: Proper lifecycle management for database and external service connections.
- **Cleanup Tasks**: Background tasks for automatic cleanup of stale resources.
- **Shutdown Hooks**: Graceful shutdown procedures that ensure all resources are properly released.

**Key files:**
- `backend/utils/dependency_manager.py` - Resource tracking and management
- `backend/utils/task_manager.py` - Task lifecycle management with cleanup
- `backend/main.py` - Application lifecycle events

### 4. Database Impact and TTL

Enhanced database interaction with caching, TTL support, and performance optimizations:

- **TTL for Cached Items**: Time-to-live implementation for cached database entries.
- **Connection Pooling**: Thread-local connection pooling for improved performance.
- **Atomic Writes**: Safe database updates using temporary files and atomic renames.
- **Cache Invalidation**: Smart cache invalidation on updates to prevent stale data.
- **Background Cleanup**: Automatic cleanup of expired database entries.

**Key files:**
- `backend/utils/db_connector.py` - Database interface with TTL caching

## Implementation Details

### Frontend Transaction Pattern

The transaction pattern works as follows:

1. Before starting a critical operation (e.g., cancelling a task), a transaction is created with `beginTransaction`.
2. The transaction ID is stored in the Redux state.
3. While the transaction is active, only updates belonging to that transaction are applied.
4. When the operation completes, `completeTransaction` is called to finalize the state.
5. A background cleanup task removes stale transactions.

Example:
```typescript
// Start a transaction
const transactionAction = beginTransaction({
  operation: 'cancel',
  taskId
});
store.dispatch(transactionAction);

// Perform operations...

// Complete the transaction
store.dispatch(completeTransaction({
  transactionId,
  success: true
}));
```

### Backend Error Handling

The error handling system provides a consistent way to raise and format errors:

```python
# Raise a standardized error
raise_error(
    "not_found",
    message="Report not found",
    detail=f"No report found with ID {report_id}",
    transaction_id=transaction_id,
    request_id=x_request_id
)

# Format an error without raising
error_response = format_error(
    "validation",
    message="Invalid input data",
    detail="The provided data did not pass validation",
    context={"errors": validation_errors}
)
```

### Resource Cleanup

Resources are tracked and cleaned up through the dependency manager:

```python
# Register a resource tracker
file_tracker = dependency_manager.register_tracker(
    "temp_files",
    lambda f: f.close(),
    "file"
)

# Register a resource
file_id = file_tracker.register(open_file, {"path": file_path})

# Release when done
file_tracker.release(file_id)
```

### Database with TTL

The database connector provides TTL-based caching:

```python
# Save a task with TTL
await db_connector.save_task(
    task_id,
    "processing",
    "report_generation",
    task_data,
    owner_id=user_id,
    ttl_hours=24  # Expires after 24 hours
)

# Get a task (uses cache with TTL)
task = await db_connector.get_task(task_id)
```

## Future Enhancements

Potential future improvements include:

1. **WebSocket Reconnection Logic**: Further enhance the WebSocket reconnection with exponential backoff and connection quality monitoring.
2. **Distributed Locking**: Implement distributed locks for multi-server deployments.
3. **Advanced Caching**: Add multi-level caching with memory and Redis/Memcached.
4. **Metrics Collection**: Add performance metrics collection for monitoring system health.
5. **API Versioning**: Implement formal API versioning for better backward compatibility.

## Technical Requirements

- **Frontend**: React 18+, Redux Toolkit
- **Backend**: FastAPI, SQLite, asyncio
- **Python Version**: 3.9+
- **Node Version**: 16+

See `backend/requirements.txt` and `frontend/package.json` for detailed dependency information. 