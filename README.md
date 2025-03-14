# Insurance Report Generator

A web-based AI-powered tool that helps insurance workers generate structured claim reports by processing uploaded files and maintaining the exact format of reference PDFs.

## Repository

This project is hosted on GitHub: [https://github.com/ButtcoinTNB/report-gen](https://github.com/ButtcoinTNB/report-gen)

## Features

- Upload reference PDFs to define report formatting and layout
- Upload case-specific documents (PDFs, Word docs, text files) for AI processing
- Generate structured reports using AI (via OpenRouter API)
- Preview reports before finalization
- Edit generated reports manually or via AI refinement
- Export reports as professionally formatted PDFs that match reference templates
- Store reports for future retrieval

## Tech Stack

### Frontend
- Next.js (React) with TypeScript
- Material UI for components
- Axios for API communication
- Deployed on Vercel

### Backend
- FastAPI (Python) for API endpoints
- PyMuPDF (fitz) for PDF text and layout extraction
- WeasyPrint and pdfrw for PDF generation and formatting
- OpenRouter API for AI text generation
- Deployed on Render

### Storage & Database
- Supabase PostgreSQL for database
- Supabase Storage for file storage

## Setup Instructions

### Prerequisites
- Node.js 18+ and npm
- Python 3.9+
- PostgreSQL (local or Supabase)

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd insurance-report-generator/backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install fastapi uvicorn sqlalchemy pydantic python-dotenv pymupdf weasyprint pdfrw httpx
   ```

4. Set up environment variables:
   - Copy `.env.example` to `.env` (in root directory)
   - Fill in your API keys and database credentials

5. Run the backend server:
   ```
   uvicorn main:app --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd insurance-report-generator/frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Run the development server:
   ```
   npm run dev
   ```

## Project Structure

```
insurance-report-generator/
│── backend/                 # FastAPI backend
│   ├── main.py              # Main FastAPI app
│   ├── api/                 # API routes
│   │   ├── upload.py        # File upload logic
│   │   ├── generate.py      # AI processing
│   │   ├── format.py        # PDF formatting
│   │   ├── edit.py          # User modifications
│   │   ├── download.py      # PDF download logic
│   ├── services/            # Utility functions
│   │   ├── pdf_extractor.py # Extracts text & layout from PDFs
│   │   ├── ai_service.py    # Calls OpenRouter API for AI generation
│   │   ├── pdf_formatter.py # Ensures output matches reference PDF
│   ├── models.py            # Database models
│   ├── config.py            # Configurations (DB, API Keys)
│── frontend/                # Next.js frontend
│   ├── pages/               # Main pages
│   │   ├── index.tsx        # File upload & report preview
│   │   ├── edit.tsx         # Edit AI-generated report
│   │   ├── download.tsx     # Download formatted PDF
│   ├── components/          # UI components
│   │   ├── UploadBox.tsx    # Drag & drop file upload
│   │   ├── ReportPreview.tsx # AI-generated report preview
│   │   ├── EditBox.tsx      # AI chat & manual editing
│   ├── styles/              # Styling (CSS/Tailwind)
│   ├── api/                 # API calls to backend
│   │   ├── upload.ts        # File upload API request
│   │   ├── generate.ts      # AI report generation API request
│   │   ├── format.ts        # Formatting API request
│   │   ├── edit.ts          # Editing API request
│   │   ├── download.ts      # PDF download API request
│── .env                     # Environment variables
│── .gitignore               # Ignore unnecessary files
│── README.md                # Documentation
│── docker-compose.yml       # (Optional) For running locally
```

## Deployment

### Backend
- Deploy to Render using the provided `requirements.txt` file
- Set environment variables in the Render dashboard

### Frontend
- Deploy to Vercel by connecting your GitHub repository
- Set environment variables in the Vercel dashboard

## License
MIT 

## Environment Variables Configuration

### Local Development

#### Frontend (.env.local)

1. Navigate to the `frontend` directory
2. Copy `.env.example` to `.env.local`
3. Set the appropriate values in `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Backend (.env)

1. Navigate to the `backend` directory
2. Copy `.env.example` to `.env`
3. Set the appropriate values in `.env`:

```env
# Supabase configuration
SUPABASE_URL=https://jkvmxxdshxyjhdoszrkv.supabase.co
SUPABASE_KEY=your-supabase-key
DATABASE_URL=postgresql://postgres:your-password@db.jkvmxxdshxyjhdoszrkv.supabase.co:5432/postgres

# API Keys
OPENROUTER_API_KEY=your-openrouter-api-key

# File storage settings
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760

# API settings
API_RATE_LIMIT=100

# LLM settings
DEFAULT_MODEL=google/gemini-2.0-pro-exp-02-05:free

# CORS settings
FRONTEND_URL=http://localhost:3000
```

### Production Deployment

#### Frontend (Vercel)

When deploying the frontend to Vercel, set the following environment variables in the Vercel dashboard:

1. Go to your Vercel project settings
2. Navigate to Environment Variables
3. Add the following variables:
   - `NEXT_PUBLIC_API_URL`: Your backend URL (e.g., https://insurance-api.onrender.com)

#### Backend (Render/Heroku)

When deploying the backend to Render or Heroku, set the environment variables in your hosting platform's dashboard:

1. Go to your app's dashboard in Render/Heroku
2. Navigate to Environment Variables or Config Vars section
3. Add all the variables from the `.env.example` file with appropriate production values:
   - Make sure `FRONTEND_URL` points to your production frontend URL (e.g., https://insurance-app.vercel.app)

## Development

### Running Locally

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

## Production Build

#### Frontend

```bash
cd frontend
npm install
npm run build
npm start
```

#### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port $PORT
``` 