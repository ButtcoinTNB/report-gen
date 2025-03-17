# Insurance Report Generator Frontend

This is the frontend application for the Insurance Report Generator, built with [Next.js](https://nextjs.org) and TypeScript. This application allows insurance workers to upload case-specific findings and generate fully formatted PDF reports based on pre-uploaded reference reports.

## Project Structure

The project follows a clean and simplified structure:

```
frontend/
├── api/                # JavaScript API client functions
├── components/         # React components
├── pages/              # Next.js pages
├── public/             # Static assets
├── styles/             # CSS and styling
├── utils/              # Utility functions including error handling
├── .next/              # Next.js build output (gitignored)
├── node_modules/       # Dependencies (gitignored)
```

## Getting Started

First, install the dependencies:

```bash
npm install
```

Then, run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the application.

## Key Features

- **File Upload**: Upload case documents and template files
- **Report Generation**: AI-powered report generation using OpenRouter API
- **Preview & Edit**: Preview and edit reports before finalizing
- **PDF Download**: Download finalized reports in PDF format

## Integration with Backend

This frontend connects to our FastAPI backend service. The API endpoints are configured through environment variables.

## Environment Variables

Create a `.env.local` file in the root directory with the following variables:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Deployment

The application is deployed on Vercel. For deployment instructions, refer to our deployment documentation or the [Next.js deployment guide](https://nextjs.org/docs/deployment).

## Learn More

For more information about the overall project architecture, refer to the main project README.
