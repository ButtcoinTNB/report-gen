# User Experience Flow

This document outlines the complete user journey through the Insurance Report Generator application, detailing each step, interactions, system responses, and error handling scenarios.

## User Journey Overview

The application follows a four-step process:

1. **Document Upload**: User uploads relevant claim documents
2. **Additional Information**: User provides any additional context or details
3. **Preview & Edit**: User reviews and can refine the generated report
4. **Download**: User downloads the finalized report in desired format

## Detailed Step Breakdown

### Step 1: Document Upload

**User Actions:**
- Navigate to the main page
- Drag and drop files or click to browse files
- Select documents related to an insurance claim (PDFs, images, Word docs)
- Review selected files list
- Click "Upload Documents" button

**System Responses:**
- Visual feedback during drag/hover state
- File type validation (accepts PDF, DOC, DOCX, TXT, images)
- Size validation (warns when approaching 100MB limit)
- Loading indicator during upload
- Progress feedback during processing

**Error States:**
- No files selected: "Please select at least one file to upload"
- File size exceeded: "Total file size exceeds 100MB limit. Please remove some files."
- Upload failed: Error message from server or generic "Failed to upload files"

**Data Flow:**
- Frontend sends files to `/api/upload/documents` endpoint
- Backend processes files and returns a report ID
- Frontend stores report ID and advances to Step 2

### Step 2: Additional Information

**User Actions:**
- Review any automatically extracted information from documents
- Add additional context in the text field
- Provide supplementary details not present in the documents
- Click "Generate Report" button

**System Responses:**
- Display of extracted information from document analysis (if available)
- Highlight fields that may need attention
- Loading indicator during background analysis
- Progress indicator during report generation

**Error States:**
- Analysis failed: Error with fallback option to continue
- Generation failed: Detailed error message with retry option

**Data Flow:**
- Frontend simultaneously:
  1. Shows Additional Info form
  2. Calls `/api/generate/analyze` to extract document data in background
- When user submits, frontend calls `/api/generate/generate` with:
  - Report ID
  - Additional information text
- Backend generates report and returns new report ID and preview URL
- Frontend advances to Step 3

### Step 3: Preview & Edit

**User Actions:**
- Review the generated report preview
- Approve report or request changes
- If changes needed:
  - Type instructions in the chat interface
  - Rate AI-generated modifications
- Click "Approve Report" when satisfied

**System Responses:**
- Display HTML preview of the report
- Chat interface for report refinement
- Loading indicator during refinement processing
- Updated preview after each refinement

**Error States:**
- Preview failed to load: Error with option to regenerate
- Refinement failed: Error message with retry option
- Timeout: Notification with option to try again

**Data Flow:**
- Frontend displays HTML preview retrieved from preview URL
- For refinements, frontend calls `/api/generate/refine` with:
  - Report ID
  - User instructions
- Backend refines report and returns updated preview URL
- When approved, frontend calls `/api/report/finalize` and advances to Step 4

### Step 4: Download

**User Actions:**
- Select desired file format (DOCX, PDF)
- Click download button
- Optionally restart the process with "Create New Report"

**System Responses:**
- Format selection options
- Loading indicator during file preparation
- Success message upon completion
- Download dialog from browser

**Error States:**
- Download preparation failed: Error with retry option
- Format conversion failed: Error with alternative format suggestion

**Data Flow:**
- Frontend calls `/api/download/{report_id}` with format parameter
- Backend prepares file and returns download URL
- Browser initiates file download

## Special Cases & Error Handling

### Lost Connection

- Application stores state in session
- Reestablishes connection and continues where left off when possible
- Shows reconnection attempt UI

### Session Expiry

- Warning notification before session expires
- Option to extend session
- Grace period to save progress

### Backend Errors

- Friendly error messages with appropriate technical details
- Retry mechanisms for transient failures
- Fallback options when appropriate

### Validation Errors

- Immediate feedback for validation issues
- Clear instructions on how to correct errors
- Prevention of form submission until errors are resolved

## Accessibility Considerations

- Keyboard navigation support throughout the application
- Screen reader compatible UI elements
- Sufficient color contrast for readability
- Loading states clearly indicated for assistive technologies

## State Management

The application handles multiple states to ensure a smooth user experience:

- **Loading States**: Visual indicators during processing
- **Error States**: Appropriate error messages with recovery options
- **Progress Tracking**: Step indicator showing current position in workflow
- **Data Persistence**: Session storage to prevent data loss

## Technical Implementation Notes

- Step transitions managed via React state
- API calls handled through async functions with proper error handling
- UI state synchronized with backend processing
- Optimistic UI updates where appropriate for faster perceived performance 