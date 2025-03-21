"use client";

import { useState } from "react";
import { 
  Box, 
  Button, 
  TextField, 
  CircularProgress, 
  Alert,
  Snackbar
} from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';
import { logger } from '../utils/logger';

interface DocxPreviewEditorProps {
  initialContent: string;
  downloadUrl: string;
}

export function DocxPreviewEditor({ initialContent, downloadUrl }: DocxPreviewEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleDownload = async () => {
    setIsLoading(true);
    setError(null);

    try {
      logger.info('Generating DOCX file...');

      const response = await fetch('/api/generate-docx', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to generate document');
      }

      // Trigger download
      window.location.href = downloadUrl;
      setShowSuccess(true);
      logger.info('DOCX file generated successfully');

    } catch (error) {
      logger.error('Error generating DOCX:', error);
      setError(error instanceof Error ? error.message : 'Failed to generate document. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <TextField
        fullWidth
        multiline
        rows={15}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        sx={{
          mb: 3,
          '& .MuiInputBase-root': {
            fontFamily: 'monospace',
            fontSize: '0.9rem'
          }
        }}
      />
      
      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleDownload}
          disabled={isLoading}
          startIcon={isLoading ? <CircularProgress size={20} /> : <DownloadIcon />}
        >
          {isLoading ? 'Generazione...' : 'Scarica DOCX'}
        </Button>
      </Box>

      <Snackbar
        open={showSuccess}
        autoHideDuration={6000}
        onClose={() => setShowSuccess(false)}
      >
        <Alert severity="success" sx={{ width: '100%' }}>
          File DOCX generato con successo!
        </Alert>
      </Snackbar>
    </Box>
  );
} 