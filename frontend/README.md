# Insurance Report Generator - Frontend

This is the frontend application for the Insurance Report Generator, built with React and Redux.

## Application Structure

The application follows a step-by-step process for generating insurance reports:

1. **Upload Documents** - Users upload insurance claim documents (PDF, DOCX, TXT)
2. **Generate Report** - AI processes the documents to generate a report
3. **Review & Edit** - Users can review, edit, and refine the report
4. **Download Report** - The final report can be downloaded in various formats

## Components

### Main Components

- `ReportStepper.js` - Manages the step-by-step process and coordinates all other components
- `FileUploader.js` - Handles document uploads with drag-and-drop and progress tracking
- `ReportGenerator.js` - Manages the report generation process with real API calls
- `ReportEditor.js` - Allows users to edit report content and request AI refinements
- `ReportDownloader.js` - Provides options for previewing and downloading the final report

### Redux State Management

The application uses Redux for state management. The main state is defined in `reportSlice.js` and includes:

```javascript
{
  activeStep: 0,                 // Current step in the process
  reportId: null,                // ID of the generated report
  loading: {                     // Loading state information
    isLoading: false,
    progress: 0,
    stage: 'initial',
    message: ''
  },
  documentIds: [],               // IDs of uploaded documents
  content: null,                 // Content of the generated report
  previewUrl: null,              // URL to preview the report
  additionalInfo: '',            // Additional information for report generation
  error: null                    // Error information
}
```

## API Integration

The frontend integrates with the backend API for various operations:

- `/api/upload/documents` - Upload documents and get document IDs
- `/api/generate` - Generate a report from uploaded documents
- `/api/generate/generate` - Generate report content based on a report ID
- `/api/edit/{reportId}` - Save edits to a report
- `/api/edit/ai-refine` - Request AI refinement of a report
- `/api/format/preview-file` - Generate a preview of the report
- `/api/download/{reportId}` - Download the report in default format
- `/api/download/docx/{reportId}` - Download the report as a DOCX file

## Getting Started

1. Install dependencies:
   ```
   npm install
   ```

2. Start the development server:
   ```
   npm start
   ```

3. Build for production:
   ```
   npm run build
   ```

## Dependencies

- React - UI library
- Redux Toolkit - State management
- Material-UI - Component library
- React Dropzone - For file upload functionality
- Axios - For API requests
