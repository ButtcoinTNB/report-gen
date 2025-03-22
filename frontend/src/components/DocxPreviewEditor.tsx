"use client";

import { useState } from "react";
import { 
  Box, 
  Button, 
  TextField, 
  CircularProgress, 
  Alert,
  Snackbar,
  Typography,
  Divider,
  Paper
} from '@mui/material';
import { Download as DownloadIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { logger } from '../utils/logger';

interface DocxPreviewEditorProps {
  initialContent: string;
  downloadUrl: string;
  reportId?: string;
  showRefinementOptions?: boolean;
  onRefinementComplete?: (data: { 
    draft: string;
    feedback: { score: number; suggestions: string[] };
    iterations: number;
    docx_url?: string;
  }) => void;
}

export function DocxPreviewEditor({ 
  initialContent, 
  downloadUrl, 
  reportId,
  showRefinementOptions = true,
  onRefinementComplete 
}: DocxPreviewEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [refinementInstructions, setRefinementInstructions] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRefining, setIsRefining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [refinementFeedback, setRefinementFeedback] = useState<{score: number; suggestions: string[]} | null>(null);

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
      setSuccessMessage('File DOCX generato con successo!');
      setShowSuccess(true);
      logger.info('DOCX file generated successfully');

    } catch (error) {
      logger.error('Error generating DOCX:', error);
      setError(error instanceof Error ? error.message : 'Failed to generate document. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefine = async () => {
    if (!refinementInstructions.trim()) {
      setError('Per favore, inserisci le istruzioni per migliorare il report.');
      return;
    }

    setIsRefining(true);
    setError(null);

    try {
      logger.info('Refining report with AI...');

      const response = await fetch('/api/agent-loop/refine-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          report_id: reportId,
          content: content,
          instructions: refinementInstructions 
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to refine report');
      }

      const data = await response.json();
      
      if (data.draft) {
        setContent(data.draft);
        setRefinementInstructions('');
        setSuccessMessage('Report migliorato con successo!');
        setShowSuccess(true);
        setRefinementFeedback(data.feedback || null);
        
        if (onRefinementComplete) {
          onRefinementComplete(data);
        }
        
        logger.info('Report refined successfully');
      } else {
        throw new Error('Invalid response format: missing draft content');
      }
    } catch (error) {
      logger.error('Error refining report:', error);
      setError(error instanceof Error ? error.message : 'Failed to refine report. Please try again.');
    } finally {
      setIsRefining(false);
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
      
      {refinementFeedback && (
        <Paper elevation={2} sx={{ p: 2, mb: 3, bgcolor: 'background.subtle' }}>
          <Typography variant="h6" gutterBottom>
            Feedback AI
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography variant="body2" sx={{ mr: 1 }}>
              Qualità del report:
            </Typography>
            <Box 
              sx={{ 
                width: '100%', 
                height: 10, 
                bgcolor: 'grey.300', 
                borderRadius: 5,
                overflow: 'hidden'
              }}
            >
              <Box 
                sx={{ 
                  width: `${refinementFeedback.score * 100}%`, 
                  height: '100%', 
                  bgcolor: refinementFeedback.score > 0.8 ? 'success.main' : 
                            refinementFeedback.score > 0.6 ? 'warning.main' : 'error.main',
                }}
              />
            </Box>
            <Typography variant="body2" sx={{ ml: 1, fontWeight: 'bold' }}>
              {Math.round(refinementFeedback.score * 100)}%
            </Typography>
          </Box>
          
          {refinementFeedback.suggestions.length > 0 && (
            <>
              <Typography variant="subtitle2" gutterBottom>
                Suggerimenti per ulteriori miglioramenti:
              </Typography>
              <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                {refinementFeedback.suggestions.map((suggestion, i) => (
                  <li key={i}>
                    <Typography variant="body2">{suggestion}</Typography>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Paper>
      )}
      
      {showRefinementOptions && (
        <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Migliora il Report con l'AI
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Descrivi cosa vorresti migliorare o correggere nel report. L'AI aggiornerà il contenuto in base alle tue istruzioni.
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={3}
            placeholder="Es. Aggiungi più dettagli sulla causa del danno, correggi il totale, migliora la struttura..."
            value={refinementInstructions}
            onChange={(e) => setRefinementInstructions(e.target.value)}
            sx={{ mb: 2 }}
            helperText={`${refinementInstructions.length}/500 caratteri - Sii specifico nelle tue istruzioni per ottenere i migliori risultati`}
            InputProps={{
              endAdornment: (
                <Box sx={{ position: 'absolute', right: 8, bottom: 8, color: 'text.secondary' }}>
                  {refinementInstructions.length > 0 && (
                    <Typography variant="caption">
                      {refinementInstructions.length}/500
                    </Typography>
                  )}
                </Box>
              ),
            }}
          />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              Esempi: "Aggiungi una sezione sul metodo di calcolo", "Riformula il paragrafo su..."
            </Typography>
            <Button
              variant="outlined"
              color="primary"
              onClick={handleRefine}
              disabled={isRefining || refinementInstructions.trim().length === 0}
              startIcon={isRefining ? <CircularProgress size={20} /> : <RefreshIcon />}
            >
              {isRefining ? 'Miglioramento in corso...' : 'Migliora Report'}
            </Button>
          </Box>
        </Paper>
      )}
      
      <Divider sx={{ mb: 3 }} />
      
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
          {successMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
} 