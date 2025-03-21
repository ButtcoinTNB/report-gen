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
  // Handle OPTIONS requests for CORS preflight
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', req.headers.origin || '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', '*');
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Access-Control-Max-Age', '86400'); // 24 hours
    res.setHeader('Access-Control-Expose-Headers', 'Content-Disposition');
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
    
    // Prepare headers to forward (ensuring they're string values)
    const forwardHeaders: Record<string, string> = {};
    
    // Only include headers we want to forward and convert arrays to strings
    Object.entries(req.headers).forEach(([key, value]) => {
      // Skip headers we don't want to forward
      if (!['host', 'connection'].includes(key.toLowerCase()) && value !== undefined) {
        // Convert array headers to comma-separated strings
        forwardHeaders[key] = Array.isArray(value) ? value.join(', ') : value;
      }
    });
    
    // Forward the request with the same body and properly formatted headers
    const response = await fetch(backendUrl, {
      method: 'POST',
      body: req.body,
      headers: {
        ...forwardHeaders,
        'Origin': req.headers.origin || '',
      },
      credentials: 'include'
    });

    // Copy CORS headers from backend response
    const corsHeaders = {
      'Access-Control-Allow-Origin': req.headers.origin || '*',
      'Access-Control-Allow-Credentials': 'true',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': '*',
      'Access-Control-Expose-Headers': 'Content-Disposition'
    };

    // Get the response data
    const data = await response.json();

    // Set CORS headers and return the response
    Object.entries(corsHeaders).forEach(([key, value]) => {
      res.setHeader(key, value);
    });

    // Return the response from the backend
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