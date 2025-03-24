import { NextApiRequest, NextApiResponse } from 'next';
import { config } from '../../../config';

/**
 * Proxy route for fetching report version history
 * This solves the issue of client-side code using relative API paths
 */
export default async function handler(
  req: NextApiRequest, 
  res: NextApiResponse
) {
  // Only allow GET requests
  if (req.method !== 'GET') {
    return res.status(405).json({ status: 'error', message: 'Method not allowed' });
  }

  try {
    const { reportId } = req.query;
    
    if (!reportId) {
      return res.status(400).json({ status: 'error', message: 'Missing reportId parameter' });
    }
    
    // Forward the request to the backend API
    const backendUrl = `${config.API_URL}/api/edit/${reportId}/versions`;
    console.log(`Forwarding version history request to: ${backendUrl}`);
    
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
    
    // Forward the request
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        ...forwardHeaders,
        'Content-Type': 'application/json'
      }
    });

    // Get the response data
    const data = await response.json();

    // Return the response from the backend
    return res.status(response.status).json(data);
  } catch (error) {
    console.error('Error forwarding version history request:', error instanceof Error ? error.message : String(error));
    return res.status(500).json({ 
      status: 'error', 
      message: 'Error forwarding request to backend', 
      error: error instanceof Error ? error.message : 'Unknown error' 
    });
  }
} 