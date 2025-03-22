import sys
import os

# Add the root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Try to import app from backend.main
    from backend.main import app
    print("Successfully imported app from backend.main")
except ModuleNotFoundError:
    # If that fails, try a different approach for Render
    print("Failed to import from backend.main directly, adjusting path...")
    
    # Check if we're in a directory that has backend subdirectory
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    if os.path.isdir(backend_dir):
        sys.path.insert(0, backend_dir)
        
        try:
            # Try to import directly from the backend directory
            import main as backend_main
            app = backend_main.app
            print("Successfully imported app from backend/main.py")
        except (ModuleNotFoundError, ImportError) as e:
            print(f"Failed to import app: {e}")
            print("Creating a minimal FastAPI app as fallback")
            
            # Create a minimal FastAPI app instance
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            
            app = FastAPI(
                title="Insurance Report Generator API",
                description="API for generating and managing insurance reports",
                version="1.0.0"
            )
            
            # Set up CORS
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["https://report-gen-liard.vercel.app"],  # For production, restrict this
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            @app.get("/health")
            async def health_check():
                return {"status": "ok", "message": "Service is running (fallback app)"}
    else:
        print("Could not find backend directory")
        raise ImportError("Could not import app from any location")

# This file serves as the main entry point for the application
# The app is defined in the backend.main module 