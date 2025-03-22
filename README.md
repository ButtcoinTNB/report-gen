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