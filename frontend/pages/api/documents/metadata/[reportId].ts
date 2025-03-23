import type { NextApiRequest, NextApiResponse } from 'next';
import { logger } from '../../../../src/utils/logger';
import { DocumentMetadata, documentService } from '../../../../src/utils/supabase';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<DocumentMetadata | { error: string }>
) {
  // Only allow GET requests
  if (req.method !== 'GET') {
    res.setHeader('Allow', ['GET']);
    return res.status(405).json({ error: `Method ${req.method} Not Allowed` });
  }

  const { reportId } = req.query;
  
  if (!reportId || typeof reportId !== 'string') {
    return res.status(400).json({ error: 'Report ID is required' });
  }

  try {
    logger.info(`Fetching metadata for report ${reportId}`);
    
    // Fetch metadata from Supabase
    const metadata = await documentService.getMetadata(reportId);
    
    return res.status(200).json(metadata);
    
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    logger.error(`Error fetching metadata for report ${reportId}: ${errorMessage}`);
    return res.status(500).json({ error: errorMessage });
  }
} 