import { NextApiRequest, NextApiResponse } from 'next';
import { config } from '../../../config';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { reportId } = req.body;
  if (!reportId) {
    return res.status(400).json({ error: 'Report ID is required' });
  }

  try {
    const backendUrl = `${config.API_URL}/agent-loop/refine-report`;
    const headers = new Headers();
    
    // Forward only necessary headers
    if (req.headers.authorization) {
      headers.append('Authorization', req.headers.authorization as string);
    }
    headers.append('Content-Type', 'application/json');

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(req.body),
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status ${response.status}`);
    }

    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error('Error in refine-report:', error);
    return res.status(500).json({ 
      error: 'Errore durante il processo di raffinamento del report',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
} 