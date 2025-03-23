import type { NextApiRequest, NextApiResponse } from 'next';
import { logger } from '../../../src/utils/logger';
import { shareService } from '../../../src/utils/supabase';

interface ShareLinkRequest {
  report_id: string;
  expiration_days?: number;
}

interface ShareLinkResponse {
  share_url: string;
  expiration_date: string;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ShareLinkResponse | { error: string }>
) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    res.setHeader('Allow', ['POST']);
    return res.status(405).json({ error: `Method ${req.method} Not Allowed` });
  }

  try {
    const { report_id, expiration_days = 7 } = req.body as ShareLinkRequest;
    
    if (!report_id) {
      return res.status(400).json({ error: 'Report ID is required' });
    }

    logger.info(`Generating share link for report ${report_id} with ${expiration_days} days expiration`);
    
    // Generate a share link using the Supabase service
    const share_url = await shareService.createShareLink(report_id, expiration_days);
    
    // Calculate expiration date
    const expirationDate = new Date();
    expirationDate.setDate(expirationDate.getDate() + expiration_days);
    
    return res.status(200).json({
      share_url,
      expiration_date: expirationDate.toISOString(),
    });
    
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    logger.error(`Error generating share link: ${errorMessage}`);
    return res.status(500).json({ error: errorMessage });
  }
} 