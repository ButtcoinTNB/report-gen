import type { NextApiRequest, NextApiResponse } from 'next';
import { runAgentLoop } from '@/lib/agents/loop';
import { extractTextFromDocs, writeToDocx } from '@/lib/docs';
import { join } from 'path';
import { writeFile } from 'node:fs/promises';
import formidable, { Fields, Files } from 'formidable';
import { File } from '@/lib/types';
import { logger } from '@/utils/logger';

export const config = {
  api: {
    bodyParser: false,
  },
};

interface AgentLoopResponse {
  draft: string;
  feedback: {
    score: number;
    suggestions: string[];
  };
  downloadUrl: string;
  iterations: number;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<AgentLoopResponse | { error: string }>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Parse multipart form data
    logger.info('Parsing form data...');
    const formData = await parseFormData(req);
    const files = formData.files;
    const additionalInfo = formData.fields.additionalInfo;

    if (!files || Object.keys(files).length === 0) {
      throw new Error('No files uploaded');
    }

    // Extract text from uploaded files
    logger.info('Extracting text from files...');
    const userContent = await extractTextFromDocs(files as unknown as File[]);

    if (!userContent.trim()) {
      throw new Error('No content could be extracted from the uploaded files');
    }

    // Run agent loop
    logger.info('Starting AI agent loop...');
    const { draft, feedback, iterations } = await runAgentLoop({
      userContent,
      additionalInfo: additionalInfo as string
    });

    logger.info(`AI agent loop completed in ${iterations} iterations`);

    // Generate docx file
    logger.info('Generating DOCX file...');
    const docxBuffer = await writeToDocx(draft);
    const filename = `report-${Date.now()}.docx`;
    const filepath = join(process.cwd(), 'public/downloads', filename);
    await writeFile(filepath, docxBuffer);

    logger.info('Report generation completed successfully');

    // Return response
    res.status(200).json({
      draft,
      feedback,
      downloadUrl: `/downloads/${filename}`,
      iterations
    });

  } catch (error) {
    logger.error('Error in agent-loop:', error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to generate report';
    res.status(500).json({ error: errorMessage });
  }
}

async function parseFormData(req: NextApiRequest): Promise<{ fields: Fields; files: File[] }> {
  return new Promise((resolve, reject) => {
    const form = formidable({
      uploadDir: '/tmp',
      keepExtensions: true,
      multiples: true,
      maxFileSize: 10 * 1024 * 1024, // 10MB limit
      filter: function ({ name, originalFilename, mimetype }: { name: string; originalFilename?: string; mimetype?: string }) {
        // Accept document and image files
        const validTypes = [
          // Documents
          'application/pdf',
          'application/msword',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'application/rtf',
          'application/vnd.oasis.opendocument.text',
          'text/plain',
          'text/csv',
          'text/html',
          'text/markdown',
          'application/vnd.ms-excel',
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          // Images
          'image/jpeg',
          'image/png',
          'image/gif',
          'image/bmp',
          'image/webp',
          'image/tiff'
        ];
        return validTypes.includes(mimetype || '');
      }
    });

    form.parse(req, (err, fields, files) => {
      if (err) {
        logger.error('Form parsing error:', err);
        return reject(err);
      }
      resolve({ fields, files: Array.isArray(files.files) ? files.files : [files.files] });
    });
  });
} 