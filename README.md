# Insurance Report Generator

An advanced web application for generating, editing, and managing insurance reports using AI-powered document analysis.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🚀 Features

- **Document Upload**: Support for various file formats (PDF, DOCX, JPG, PNG)
- **Chunked Uploads**: Handle large files efficiently
- **AI-Powered Analysis**: Extract relevant information from insurance documents
- **Report Generation**: Create structured reports based on document analysis
- **Interactive Editing**: Edit and refine generated reports
- **Multiple Export Formats**: Download reports in various formats (PDF, DOCX, TXT)
- **Real-time Updates**: WebSocket integration for progress tracking
- **Responsive UI**: Modern interface that works on desktop and mobile

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+
- PostgreSQL 13+ (or Supabase account)
- OpenAI API key or compatible AI service

## 🛠️ Installation

### Clone the Repository

```bash
git clone https://github.com/yourusername/insurance-report-generator.git
cd insurance-report-generator
```

### Setting Up the Backend

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Configure environment variables:

```bash
# Run the environment setup script
python backend/scripts/setup_env.py --env local

# Edit the environment variables
nano backend/.env
```

4. Run the backend server:

```bash
cd backend
uvicorn main:app --reload
```

### Setting Up the Frontend

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Run the development server:

```bash
npm run dev
```

## 🚀 Using the Application

1. Open your browser and navigate to `http://localhost:3000`
2. Upload insurance-related documents
3. Wait for the AI to process the documents
4. Review and edit the generated report
5. Export the report in your preferred format

## 🌍 Production Deployment

### Backend Deployment on Render

For detailed instructions on deploying the backend to Render, see [Render Deployment Guide](docs/RENDER_DEPLOYMENT.md).

### Frontend Deployment on Vercel

For detailed instructions on deploying the frontend to Vercel, see [Vercel Deployment Guide](docs/VERCEL_DEPLOYMENT.md).

### Production Checklist

Before deploying to production, go through the [Production Checklist](docs/PRODUCTION_CHECKLIST.md) to ensure your application is properly configured.

## �� Configuration

### Backend Configuration

Key environment variables for the backend:

| Variable | Description | Default |
|----------|-------------|---------|
| OPENAI_API_KEY | API key for OpenAI | - |
| SUPABASE_URL | URL for Supabase | - |
| SUPABASE_KEY | API key for Supabase | - |
| UPLOAD_DIR | Directory for uploaded files | ./uploads |
| GENERATED_DIR | Directory for generated reports | ./generated |
| DATA_RETENTION_HOURS | Hours to keep data before cleanup | 24 |
| DEBUG | Enable debug mode | false |
| ALLOWED_ORIGINS | CORS allowed origins | http://localhost:3000 |
| API_RATE_LIMIT | Rate limit for API requests | 100 |
| AI_SERVICE | AI service provider | openai |

See `.env.example` for a complete list of configuration options.

### Frontend Configuration

Key environment variables for the frontend:

| Variable | Description | Default |
|----------|-------------|---------|
| NEXT_PUBLIC_API_URL | URL of the backend API | http://localhost:8000 |
| NEXT_PUBLIC_WS_URL | WebSocket URL | ws://localhost:8000 |

## 🧪 Testing

Run backend tests:

```bash
cd insurance-report-generator
./run_tests.sh
```

Run frontend tests:

```bash
cd frontend
npm test
```

## 🔒 Security Considerations

- API rate limiting is enabled by default
- Input validation on all endpoints
- File type and size restrictions
- Sanitization of user inputs
- Regular data cleanup to prevent storage overflow

## 📖 API Documentation

For detailed API documentation, see [API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md).

## 🏗️ Architecture

The application follows a client-server architecture:

- **Frontend**: Next.js React application
- **Backend**: FastAPI Python application
- **Database**: PostgreSQL (via Supabase)
- **File Storage**: Local filesystem or Supabase Storage
- **AI Processing**: OpenAI API or compatible service

### Backend Components:

- **API Layer**: FastAPI routes handling requests
- **Service Layer**: Business logic and AI integration
- **Data Layer**: Database access and file handling
- **Background Tasks**: Processing long-running operations

### Frontend Components:

- **Upload Module**: File upload and chunking
- **Editor Module**: Report viewing and editing
- **Export Module**: Report formatting and downloading
- **Notification System**: Real-time updates via WebSockets

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👏 Acknowledgments

- OpenAI for providing the AI capabilities
- FastAPI for the efficient backend framework
- Next.js team for the frontend framework
- All contributors who have helped with the project 