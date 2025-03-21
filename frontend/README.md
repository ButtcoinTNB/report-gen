# Insurance Report Generator - Frontend

This is the frontend application for the Insurance Report Generator, built with React, Redux, and TypeScript.

## Application Structure

The application follows a step-by-step process for generating insurance reports:

1. **Upload Documents** - Users upload insurance claim documents (PDF, DOCX, TXT)
2. **Generate Report** - AI processes the documents to generate a report
3. **Review & Edit** - Users can review, edit, and refine the report
4. **Download Report** - The final report can be downloaded in various formats

## Directory Structure

The frontend follows the standard Next.js with TypeScript project structure:

```
frontend/
├── pages/           # Next.js pages and API routes
│   └── api/         # API proxy routes
├── src/             # Source code
│   ├── components/  # React components
│   ├── services/    # API services
│   ├── store/       # Redux store
│   ├── types/       # TypeScript types
│   └── utils/       # Utility functions
├── public/          # Static assets
├── styles/          # Global styles
└── config.ts        # Application configuration
```

## Components

### Main Components

- `ReportStepper.tsx` - Manages the step-by-step process and coordinates all other components
- `FileUploader.tsx` - Handles document uploads with drag-and-drop and progress tracking
- `ReportGenerator.tsx` - Manages the report generation process with real API calls
- `ReportEditor.tsx` - Allows users to edit report content and request AI refinements
- `ReportDownloader.tsx` - Provides options for previewing and downloading the final report

### Redux State Management

The application uses Redux for state management. The main state is defined in `reportSlice.ts` and includes:

```typescript
interface ReportState {
  activeStep: number;           // Current step in the process
  reportId: string | null;      // ID of the generated report
  loading: LoadingState;        // Loading state information
  documentIds: string[];        // IDs of uploaded documents
  content: string | null;       // Content of the generated report
  previewUrl: string | null;    // URL to preview the report
  additionalInfo: string;       // Additional information for report generation
  error: string | null;         // Error information
}

interface LoadingState {
  isLoading: boolean;
  progress: number;
  stage: 'initial' | 'uploading' | 'analyzing' | 'generating' | 'refining' | 'preview' | 'downloading' | 'formatting' | 'saving' | 'complete' | 'error';
  message: string;
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
   npm run dev
   ```

3. Build for production:
   ```
   npm run build
   ```

## Dependencies

- React - UI library
- Redux Toolkit - State management
- TypeScript - Type safety
- Material-UI - Component library
- React Dropzone - For file upload functionality
- Next.js - React framework
