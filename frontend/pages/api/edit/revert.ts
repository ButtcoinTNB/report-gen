import { NextApiRequest, NextApiResponse } from 'next';
import { config } from '../../../config';

/**
 * Proxy route for reverting to previous versions of a report
 * This solves the issue of client-side code using relative API paths
 */
export default async function handler(
  req: NextApiRequest, 
  res: NextApiResponse
) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({ status: 'error', message: 'Method not allowed' });
  }

  try {
    const { reportId, versionNumber } = req.query;
    
    if (!reportId || !versionNumber) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'Missing required parameters: reportId and versionNumber' 
      });
    }
    
    // Forward the request to the backend API
    const backendUrl = `${config.API_URL}/api/edit/${reportId}/revert/${versionNumber}`;
    console.log(`Forwarding revert request to: ${backendUrl}`);
    
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
      method: 'POST',
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
    console.error('Error forwarding revert request:', error instanceof Error ? error.message : String(error));
    return res.status(500).json({ 
      status: 'error', 
      message: 'Error forwarding request to backend', 
      error: error instanceof Error ? error.message : 'Unknown error' 
    });
  }
} 