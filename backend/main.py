from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

# Import API route modules
from api import upload, generate, format, edit, download
from config import settings

# Ensure required directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("generated_reports", exist_ok=True)
print(f"Ensured directories exist: {settings.UPLOAD_DIR}, generated_reports")

app = FastAPI(
    title="Scrittore Automatico di Perizie",
    description="API for generating structured insurance claim reports",
    version="0.1.0",
)

# Get allowed origins - split by comma if it's a list
frontend_urls = settings.FRONTEND_URL.split(',') if ',' in settings.FRONTEND_URL else [settings.FRONTEND_URL]

# Add Vercel domain explicitly
allowed_origins = frontend_urls + [
    "https://report-gen-liard.vercel.app",
    "https://report-gen.vercel.app",
    "https://report-gen-5wtl.onrender.com",  # Add Render domain
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

print(f"CORS allowed origins: {allowed_origins}")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for debugging
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Include OPTIONS for preflight
    allow_headers=["*"],
    max_age=86400,  # Cache preflight request for 24 hours
)

# Include API routes
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(generate.router, prefix="/api/generate", tags=["Generate"])
app.include_router(format.router, prefix="/api/format", tags=["Format"])
app.include_router(edit.router, prefix="/api/edit", tags=["Edit"])
app.include_router(download.router, prefix="/api/download", tags=["Download"])


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the Scrittore Automatico di Perizie API"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
