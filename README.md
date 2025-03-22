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