# Development Guidelines

This document provides guidelines, best practices, and troubleshooting tips for developers working on the Insurance Report Generator application.

## Development Environment Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- PostgreSQL (local or Supabase)
- Git

### Backend Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd insurance-report-generator
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the application in development mode:
   ```bash
   pip install -e .
   ```

4. Install the backend requirements:
   ```bash
   pip install -r backend/requirements.txt
   ```

5. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Then edit the `.env` file with your actual configuration values.

6. Run the backend server:
   ```bash
   python main.py
   ```
   The API will be available at http://localhost:8000

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env.local
   ```
   Then edit the `.env.local` file with your actual configuration values.

4. Run the development server:
   ```bash
   npm run dev
   ```
   The frontend will be available at http://localhost:3000

## TypeScript Development Guidelines

### TypeScript Version

The project uses TypeScript 4.9+. Ensure your IDE/editor has TypeScript support installed.

### Component Structure

1. All React components should be written in TypeScript (`.tsx` files)
2. Components should be located in the `frontend/src/components` directory
3. Each component should have its props interface defined:

```tsx
interface ButtonProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'outline';
}

const Button: React.FC<ButtonProps> = ({ label, onClick, disabled = false, variant = 'primary' }) => {
  // Component implementation
};
```

### Type Safety

1. Avoid using `any` type whenever possible
2. Define interfaces for all API responses and requests
3. Use TypeScript's utility types when appropriate (`Partial<T>`, `Pick<T>`, etc.)
4. Enable strict type checking in `tsconfig.json`

### Importing Components

Always import components from the `src/components` directory:

```tsx
// Correct
import { Button } from '../src/components';
import TextField from '../src/components/TextField';

// Incorrect - Do not use these patterns
import { Button } from '../components';
import TextField from 'frontend/components/TextField';
```

### Type Organization

1. Shared types should be in the `frontend/src/types` directory
2. Component-specific types can be defined in the component file
3. Export/import types as needed to maintain DRY principles

## Code Style and Standards

### Backend (Python)

- Follow PEP 8 style guidelines
- Use type hints when possible
- Document all functions and classes with docstrings
- Maintain consistent error handling using the utils.error_handler module
- Keep functions and methods focused on a single responsibility
- Use meaningful variable and function names

### Frontend (JavaScript/TypeScript)

- Follow ESLint rules as defined in the project
- Use TypeScript for new components
- Document complex functions with JSDoc comments
- Use React functional components and hooks
- Keep components focused on a single responsibility
- Follow the established project structure

## Common Development Tasks

### Adding a New API Endpoint

1. Identify the appropriate router file in `backend/api/`
2. Add the new endpoint function
3. Document the function with docstrings
4. Implement proper error handling
5. Return consistent response formats
6. Update the API documentation

Example:
```python
@router.post("/my-new-endpoint")
async def my_new_endpoint(request: MyRequestModel):
    """
    Description of what this endpoint does.
    
    Args:
        request: The request model containing required fields
        
    Returns:
        Response with appropriate data
        
    Raises:
        HTTPException: If something goes wrong
    """
    try:
        # Implementation
        return {"status": "success", "data": result}
    except Exception as e:
        handle_exception(e, "My New Endpoint")
        raise
```

### Adding a New Frontend Component

1. Create a new file in `frontend/components/`
2. Use TypeScript for the component definition
3. Follow the established styling patterns
4. Add appropriate prop validations
5. Include error handling and loading states

Example:
```tsx
import React from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';

interface MyComponentProps {
  data: any;
  isLoading: boolean;
  onAction: () => void;
}

const MyComponent: React.FC<MyComponentProps> = ({ data, isLoading, onAction }) => {
  if (isLoading) {
    return <CircularProgress />;
  }
  
  return (
    <Box>
      <Typography variant="h6">My Component</Typography>
      {/* Component implementation */}
    </Box>
  );
};

export default MyComponent;
```

## Debugging Tips

### Backend

- Check the logs in `backend/logs/`
- Use the `/debug` endpoint to check environment and imports
- Set up debug breakpoints in your IDE
- Make use of Python's `logging` module

### Frontend

- Use React DevTools for component inspection
- Check the browser console for errors
- Use the Network tab to inspect API calls
- Add `console.log` statements for debugging (but remove them before committing)

## Common Issues and Solutions

### Backend Import Issues

Issue: "Module not found" errors when running the backend

Solution:
- Make sure the application is installed with `pip install -e .`
- Check that the project root is in the Python path
- Ensure proper imports using absolute paths

### Frontend API Connection Issues

Issue: Frontend cannot connect to the backend API

Solution:
- Confirm the backend server is running
- Check the `NEXT_PUBLIC_API_URL` in `.env.local`
- Verify CORS settings in `backend/main.py`
- Check for network errors in the browser console

### PDF Processing Issues

Issue: PDF text extraction not working correctly

Solution:
- Check that PyMuPDF is installed properly
- Ensure the PDF is not password-protected
- Try with a different PDF to isolate the issue
- Check the logs for PyMuPDF errors

## Performance Considerations

### Backend Optimization

- Use async functions for I/O bound operations
- Consider background tasks for long-running processes
- Implement proper caching strategies
- Monitor memory usage, especially for PDF processing

### Frontend Optimization

- Lazy-load components when appropriate
- Optimize image sizes
- Use React.memo for expensive components
- Implement virtualization for long lists

## Deployment

### Backend (Render)

1. Connect your repository to Render
2. Set up as a Web Service
3. Use the following settings:
   - Build Command: `pip install -e . && pip install -r backend/requirements.txt`
   - Start Command: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add all necessary environment variables from `.env.example`

### Frontend (Vercel)

1. Connect your repository to Vercel
2. Set the following settings:
   - Framework Preset: Next.js
   - Root Directory: frontend
3. Add all necessary environment variables from `.env.example`

## Testing

### Backend Tests

- Use pytest for testing
- Run tests with `pytest backend/tests/`
- Write unit tests for critical services
- Mock external dependencies

### Frontend Tests

- Use Jest and React Testing Library
- Run tests with `npm test`
- Focus on component and integration tests
- Mock API calls using tools like msw 