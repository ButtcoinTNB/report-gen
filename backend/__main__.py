"""
Entry point for the backend package.
This allows running the app directly with 'python -m backend'.
"""

import uvicorn

if __name__ == "__main__":
    print("Starting FastAPI application...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
