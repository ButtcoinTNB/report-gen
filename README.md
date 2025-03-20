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

- **Frontend**: Next.js, TypeScript, Material-UI
- **Backend**: FastAPI, Python, SQLAlchemy
- **Database**: Supabase (PostgreSQL)
- **AI**: OpenRouter API (Claude 3)
- **File Processing**: PyMuPDF, WeasyPrint, PDFrw
- **Deployment**: Vercel (Frontend), Render (Backend)

## Prerequisites

- Node.js 18+ and npm
- Python 3.8+
- Supabase account
- OpenRouter API key

## Installation

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
   - Copy `.env.example` from the root directory to `backend/.env`
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

3. Set up environment variables:
   - Copy `.env.example` from the root directory to `frontend/.env.local`
   - Update the `NEXT_PUBLIC_API_URL` to point to your backend service

4. Start the development server:
   ```
   npm run dev
   ```

## Environment Variables Configuration

### Local Development

The project uses a consolidated `.env.example` file in the root directory that contains all necessary environment variables for both frontend and backend. This file is organized into sections:

- **Backend Configuration**: Database, API keys, file storage, and AI settings
- **Frontend Configuration**: API URLs and public variables
- **Development Settings**: Environment and debug modes

To set up environment variables:

1. **For Backend**:
   - Copy `.env.example` from the root to `backend/.env`
   - Update the values in `backend/.env`

2. **For Frontend**:
   - Copy `.env.example` from the root to `frontend/.env.local`
   - Update the values in `frontend/.env.local`

### Production Deployment

When deploying the application:

1. **Backend (Render/Heroku)**:
   - Set all backend variables from the `.env.example` file in your hosting platform's dashboard
   - Ensure `FRONTEND_URL` points to your production frontend URL

2. **Frontend (Vercel)**:
   - Set all frontend variables from the `.env.example` file in your Vercel project settings
   - Update `NEXT_PUBLIC_API_URL` to point to your production backend URL

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
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn main:app --reload
```

### Testing

Run tests using pytest:

```bash
cd backend
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
MIT 

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