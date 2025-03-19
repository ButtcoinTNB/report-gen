# Cursor Rules for Insurance Report Generator

This document provides a high-level overview of the Insurance Report Generator application, its architecture, and key components. Use this as a reference guide to understand the codebase structure and design decisions.

## Project Overview

The Insurance Report Generator (Scrittore Automatico di Perizie) is a web-based AI-powered tool designed to help insurance professionals generate structured claim reports. It processes uploaded documents (PDFs, Word files, text files), extracts relevant information, and generates professional reports that match reference templates.

### Key Features

- Document upload and analysis
- AI-powered information extraction
- Report generation with proper formatting
- Report preview and refinement capabilities
- DOCX and PDF download options
- Error handling and user feedback mechanisms

## Architecture

The application uses a modern two-tier architecture:

### Frontend (Next.js/React)
- Written in TypeScript and JavaScript
- Material UI for component styling
- Deployed on Vercel

### Backend (FastAPI)
- Python-based REST API
- Handles document processing, AI interactions, and report generation
- Deployed on Render

## Directory Structure

```
insurance-report-generator/
│── backend/                 # FastAPI backend
│   ├── api/                 # API routes and endpoints
│   ├── services/            # Core business logic and utilities
│   └── utils/               # Helper functions and utilities
│── frontend/                # Next.js frontend
│   ├── api/                 # API client functions
│   ├── components/          # React UI components
│   ├── pages/               # Next.js page routes
│   └── utils/               # Frontend utilities
```

## Data Flow

1. User uploads documents via frontend
2. Backend processes uploaded files
3. AI extracts relevant information
4. User adds additional information if needed
5. Report is generated based on the extracted info
6. User can preview, refine, and download the report

## Key Code Files

### Backend

- `backend/main.py`: FastAPI application setup
- `backend/api/generate.py`: Report generation logic
- `backend/api/upload.py`: File upload handling
- `backend/services/ai_service.py`: AI processing logic
- `backend/services/docx_service.py`: Document formatting

### Frontend

- `frontend/pages/index.js`: Main application page
- `frontend/components/FileUpload.tsx`: Document upload component
- `frontend/api/generate.js`: Report generation API client
- `frontend/api/upload.js`: File upload API client

## Environment Configuration

The application relies on environment variables for configuration:

- Backend: `.env` file in the root directory
- Frontend: `.env.local` file in the frontend directory

## Key Dependencies

- OpenRouter API for AI capabilities
- PyMuPDF for PDF processing
- DOCX template for document formatting
- Material UI for frontend components
- Axios for API communication

## Deployment

- Backend: Deployed on Render
- Frontend: Deployed on Vercel
- Database: Supabase PostgreSQL
- File Storage: Supabase Storage or local filesystem

## Additional Notes

- The code is structured to be maintainable and scalable
- Error handling is implemented throughout the application
- The application is designed to be responsive and user-friendly 