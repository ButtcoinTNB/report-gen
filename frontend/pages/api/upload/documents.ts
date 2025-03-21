import { NextApiRequest, NextApiResponse } from 'next';
import { config } from '../../../config';

/**
 * Proxy route for uploading documents to the backend API
 * This solves the issue of client-side code using relative API paths
 */
export default async function handler(
  req: NextApiRequest, 
  res: NextApiResponse
) {
  // Set CORS headers for all responses
  const corsHeaders = {
    'Access-Control-Allow-Origin': req.headers.origin || '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Max-Age': '86400',
    'Access-Control-Expose-Headers': 'Content-Disposition'
  };

  // Set CORS headers for all responses
  Object.entries(corsHeaders).forEach(([key, value]) => {
    res.setHeader(key, value);
  });

  // Handle OPTIONS request (preflight)
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // Only allow POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({ status: 'error', message: 'Method not allowed' });
  }

  try {
    // Forward the request to the backend API
    const backendUrl = `${config.API_URL}/api/upload/documents`;
    console.log(`Forwarding upload request to: ${backendUrl}`);
    
    // Prepare headers to forward
    const forwardHeaders: Record<string, string> = {
      ...corsHeaders,
      'Origin': req.headers.origin || '',
      'Content-Type': req.headers['content-type'] || 'application/json'
    };
    
    // Forward the request
    const response = await fetch(backendUrl, {
      method: 'POST',
      body: req.body,
      headers: forwardHeaders,
      credentials: 'include'
    });

    // Get the response data
    const data = await response.json();

    // Return the response with appropriate status code
    return res.status(response.status).json(data);
  } catch (error) {
    console.error('Error forwarding upload request:', error instanceof Error ? error.message : String(error));
    return res.status(500).json({ 
      status: 'error', 
      message: 'Error forwarding request to backend', 
      error: error instanceof Error ? error.message : 'Unknown error' 
    });
  }
} 