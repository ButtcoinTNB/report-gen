import { NextApiRequest, NextApiResponse } from 'next';
import { config } from '../../../../config';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { taskId } = req.query;
  if (!taskId || Array.isArray(taskId)) {
    return res.status(400).json({ error: 'Invalid task ID' });
  }

  // Set headers for SSE
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  try {
    const backendUrl = `${config.API_URL}/agent-loop/task-events/${taskId}`;
    const headers = new Headers();
    if (req.headers.authorization) {
      headers.append('Authorization', req.headers.authorization as string);
    }

    const response = await fetch(backendUrl);
    if (!response.ok) {
      throw new Error(`Backend responded with status ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No reader available from backend response');
    }

    // Forward SSE events from backend to client
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = new TextDecoder().decode(value);
      res.write(chunk);

      // Check if client disconnected
      if (res.writableEnded) {
        reader.cancel();
        break;
      }
    }

    res.end();
  } catch (error) {
    console.error('Error in task-events:', error);
    res.end(`event: error\ndata: ${JSON.stringify({ 
      error: 'Errore durante il monitoraggio del task',
      details: error instanceof Error ? error.message : 'Unknown error'
    })}\n\n`);
  }
} 