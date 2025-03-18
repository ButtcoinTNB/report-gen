// API route to check frontend configuration
import { config } from '../../config';

export default function handler(req, res) {
  // Return the configuration without sensitive values
  res.status(200).json({
    apiUrl: config.API_URL,
    buildTime: new Date().toISOString(),
    endpoints: {
      ...config.endpoints
    },
    nodeEnv: process.env.NODE_ENV,
    // Add additional non-sensitive information here
  });
} 