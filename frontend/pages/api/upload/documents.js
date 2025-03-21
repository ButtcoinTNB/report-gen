import { config } from '../../../config';

/**
 * Proxy route for uploading documents to the backend API
 * This solves the issue of client-side code using relative API paths
 */
export default async function handler(req, res) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({ status: 'error', message: 'Method not allowed' });
  }

  try {
    // Forward the request to the backend API
    const backendUrl = `${config.API_URL}/api/upload/documents`;
    console.log(`Forwarding upload request to: ${backendUrl}`);
    
    // Forward the request with the same body and headers
    const response = await fetch(backendUrl, {
      method: 'POST',
      body: req.body,
      headers: {
        // Filter out headers that shouldn't be forwarded
        ...Object.fromEntries(
          Object.entries(req.headers)
            .filter(([key]) => !['host', 'connection'].includes(key.toLowerCase()))
        ),
      },
    });

    // Get the response data
    const data = await response.json();

    // Return the response from the backend
    return res.status(response.status).json(data);
  } catch (error) {
    console.error('Error forwarding upload request:', error);
    return res.status(500).json({ 
      status: 'error', 
      message: 'Error forwarding request to backend', 
      error: error.message 
    });
  }
} 