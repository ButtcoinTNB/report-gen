import { NextApiRequest, NextApiResponse } from 'next';
import { config } from '../../config';

/**
 * Test route for verifying configuration
 * Responds with the current configuration (removing any sensitive values)
 */
export default function handler(
  req: NextApiRequest, 
  res: NextApiResponse
) {
  // Return the API configuration (sanitized)
  res.status(200).json({
    status: 'success',
    message: 'Config check successful',
    apiUrl: config.API_URL,
    endpoints: config.endpoints,
    env: process.env.NODE_ENV,
    // Include timestamp for cache debugging
    timestamp: new Date().toISOString()
  });
} 