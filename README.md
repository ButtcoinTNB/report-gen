# Scrittore Automatico di Perizie

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
│   │   ├── services/        # Utility functions
│   │   │   ├── pdf_extractor.py # Extracts text & layout from PDFs
│   │   │   ├── ai_service.py    # Calls OpenRouter API for AI generation
│   │   │   ├── pdf_formatter.py # Ensures output matches reference PDF
│   │   ├── models.py            # Database models
│   │   ├── config.py            # Configurations (DB, API Keys)
│   │   └── .env.example        # Environment variables
│   ├── .env                     # Environment variables
│   └── .gitignore               # Ignore unnecessary files
│   └── README.md                # Documentation
│   └── docker-compose.yml       # (Optional) For running locally
│── frontend/                   # Next.js frontend
│   ├── api/                    # JavaScript API client functions
│   ├── components/             # React components (TypeScript)
│   │   ├── FileUpload.tsx      # File upload component
│   │   ├── ReportPreview.tsx   # Report preview component
│   │   ├── DownloadReport.tsx  # Report download component
│   │   ├── Navbar.tsx          # Navigation component
│   │   └── ReportGenerator.tsx # Report generation component
│   ├── pages/                  # Next.js pages
│   │   ├── index.js            # Home page
│   │   └── edit.tsx            # Report editing page
│   ├── utils/                  # Utility functions
│   │   └── errorHandler.js     # Standardized error handling
│   ├── public/                 # Static assets
│   ├── styles/                 # CSS styling
│   ├── .env.local              # Environment variables (local)
│   └── README.md               # Frontend documentation
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
MAX_UPLOAD_SIZE=104857600  # 100MB

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

# Insurance Report Generator - Template System

This system uses AI to dynamically generate insurance reports in DOCX format based on uploaded documents and user inputs.

## Key Features

- **Dynamic Variable Extraction**: Automatically extracts key information from uploaded documents using AI and OCR.
- **Rich Text Formatting**: Supports bullet points, bold, italic, and other formatting in the generated reports.
- **Template-Based Generation**: Uses DOCX templates with variable placeholders that are filled by the AI.
- **Preview and Refinement**: Allows users to preview and refine generated reports before final download.

## How It Works

1. **Upload Documents**: Users upload PDFs, images, DOCX files, or text files containing relevant information.
2. **OCR Processing**: The system extracts text from all documents, including images and scanned PDFs.
3. **AI Analysis**: An AI model (via OpenRouter API) extracts structured data from the text.
4. **Template Filling**: The extracted data is used to fill a DOCX template with placeholders.
5. **Refinement**: Users can provide instructions to refine the report content.
6. **Download**: The final DOCX report is generated for download.

## Templates

Templates are DOCX files with Jinja2-style variables using the syntax `{{ variable_name }}`. For example:

```
Nome azienda: {{ nome_azienda }}
Indirizzo: {{ indirizzo_azienda }}, {{ cap }} {{ city }}
Data: {{ data_oggi }}

Riferimento cliente: {{ vs_rif }}
Numero polizza: {{ polizza }}

Dinamica degli eventi:
{{ dinamica_eventi_accertamenti }}
```

### Variable Types

The system supports various variable types:

- **Text fields**: Basic text replacement (`{{ nome_azienda }}`)
- **Rich text fields**: Fields that support formatting like bullet points (`{{ dinamica_eventi_accertamenti }}`)
- **Date fields**: Automatically formatted in Italian style (`{{ data_oggi }}`)
- **Monetary fields**: Properly formatted with euro symbol (`{{ totale_danno }}`)

### Common Variables

These are the most commonly used variables in templates:

- `nome_azienda`: Company name
- `indirizzo_azienda`: Company address
- `cap`: Postal code
- `city`: City
- `data_oggi`: Current date in Italian format (e.g., "18 Marzo 2025")
- `vs_rif`: Customer reference
- `rif_broker`: Broker reference
- `polizza`: Policy number
- `ns_rif`: Internal reference
- `oggetto_polizza`: Policy object
- `assicurato`: Insured name
- `data_sinistro`: Date of incident
- `titolo_breve`: Brief description
- `luogo_sinistro`: Location of incident
- `dinamica_eventi_accertamenti`: Detailed description of events (with bullet points)
- `totale_danno`: Total damage amount
- `causa_danno`: Cause of damage
- `lista_allegati`: List of attachments (with bullet points)

## Testing Templates

You can test templates with the provided script:

```bash
python test_template_processing.py --template templates/template.docx --output output.docx
```

This will generate a sample report using example data.

## Integration

The template system is integrated into the main API through these endpoints:

- `POST /api/generate`: Generates a report from uploaded documents
- `POST /api/reports/{report_id}/refine`: Refines an existing report based on user instructions

## Requirements

- Python 3.8+
- Tesseract OCR
- Required Python packages listed in `requirements.txt`

## Installation

1. Install required dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Install Tesseract OCR:
   ```bash
   # On macOS
   brew install tesseract
   
   # On Ubuntu/Debian
   apt-get install tesseract-ocr
   ```

3. Place your template.docx in the templates directory.

4. Configure environment variables in `.env`.

5. Run the API server:
   ```bash
   uvicorn backend.main:app --reload
   ``` 