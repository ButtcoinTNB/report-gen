# Installation Guide

## Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd insurance-report-generator
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install the application in development mode:
   ```bash
   pip install -e .
   ```

4. Install the requirements:
   ```bash
   pip install -r backend/requirements.txt
   ```

5. Set up environment variables by copying the example file:
   ```bash
   cp .env.example backend/.env
   ```
   
   Then edit the `backend/.env` file with your actual configuration values.

6. Run the application:
   ```bash
   python main.py
   ```
   
   The API will be available at http://localhost:8000

## Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables by copying the example file:
   ```bash
   cp ../.env.example .env.local
   ```
   
   Then edit the `.env.local` file with your actual configuration values.

4. Start the development server:
   ```bash
   npm run dev
   ```

## Deployment on Render

For Render deployment, make sure to:

1. Add the repository to Render
2. Set up as a Web Service
3. Use the following settings:
   - Build Command: `pip install -e . && pip install -r backend/requirements.txt`
   - Start Command: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add all necessary environment variables from the `.env.example` file in the root directory

## Troubleshooting

If you encounter import errors:

1. Make sure the application is installed with `pip install -e .`
2. The root directory should be in the Python path
3. Check that all required environment variables are set 