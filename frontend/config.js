/**
 * Frontend configuration
 * Manages environment variables for API URLs and other settings
 */

// In production (Vercel), use the NEXT_PUBLIC_API_URL environment variable
// In development, fall back to localhost
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const config = {
  API_URL,
  endpoints: {
    upload: `${API_URL}/api/upload`,
    generate: `${API_URL}/api/generate`,
    format: `${API_URL}/api/format`,
    edit: `${API_URL}/api/edit`,
    download: `${API_URL}/api/download`,
  }
};

export default config; 