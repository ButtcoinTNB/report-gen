# Backend Build Fix for Render

This document provides troubleshooting steps for fixing the backend build failures on Render.

## Issue

The Render build is failing after dependencies are downloaded, but without a clear error message. This could be due to several issues:

1. Missing packages in `requirements.txt`
2. Incorrect build command
3. Python version compatibility issues
4. Incompatible package versions

## Solutions

### 1. Update Build Command

Make sure your build command is correctly specified in Render. The recommended build command is:

```
pip install -r requirements.txt && cd backend && pip install -e .
```

This ensures that if your backend has a setup.py file, it will be installed in development mode.

### 2. Check Python Version

Ensure you're using a compatible Python version. Render's logs show it's using Python 3.11.11. Make sure your code is compatible with this version.

You can specify a different Python version in your Render dashboard if needed:

1. Go to your Render dashboard
2. Select your backend service
3. Go to "Settings" > "Environment"
4. Add an environment variable: `PYTHON_VERSION=3.9.16` (or your preferred version)

### 3. Update requirements.txt

Make sure your `requirements.txt` includes all necessary dependencies with compatible versions. Add the following to the top of your file to ensure proper dependency resolution:

```
--no-binary :all:
wheel>=0.38.4
setuptools>=65.5.1
```

### 4. Fix Package Conflicts

If there are package conflicts, try:

1. Pinning specific versions of problematic dependencies
2. Creating a separate `requirements-render.txt` for production deployments

### 5. Debug Build with Custom Start Command

To debug build issues, temporarily change your start command to:

```
cd backend && python -c "import sys; print(sys.path); import os; print(os.environ)"
```

This will show the Python path and environment variables, which can help diagnose import issues.

### 6. Fix Common Build Issues

#### Missing System Dependencies

If you're using packages that require system libraries (like `psycopg2` or packages with C extensions), add a `build.sh` file to your repository:

```bash
#!/bin/bash
# build.sh
apt-get update
apt-get install -y tesseract-ocr libmagic-dev poppler-utils
pip install -r requirements.txt
```

Then update your build command in Render to:
```
chmod +x ./build.sh && ./build.sh
```

#### File Permissions

Ensure any scripts you're running have correct permissions:

```bash
chmod +x backend/scripts/*.py
```

#### Setup Script for Environment Variables

Create a setup script that runs before your application starts:

```bash
# backend/scripts/render_setup.py
import os
import sys

# Create necessary directories
dirs = ['uploads', 'generated_reports', 'temp']
for dir_name in dirs:
    os.makedirs(os.path.join('/opt/render/project/src', dir_name), exist_ok=True)

print("Setup completed successfully!")
```

Update your start command to run this script:
```
cd backend && python scripts/render_setup.py && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 7. Update Render Configuration

Ensure your Render configuration includes:

1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
3. **Root Directory**: If your repository has a specific structure, make sure the root directory is set correctly

### 8. Check for Circular Imports

Check your Python code for circular imports, which can cause issues during startup. Resolve circular dependencies by:

1. Moving imports inside functions (lazy imports)
2. Restructuring your code to avoid circular references
3. Using proper dependency injection patterns

## Testing Locally Before Deployment

Test your build process locally to identify issues before deploying to Render:

```bash
# Create a clean virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install dependencies as Render would
pip install -r requirements.txt

# Test startup
cd backend
python -m uvicorn main:app
```

If the application starts successfully locally but fails on Render, the issue is likely environment-specific. 