"use client";

import { useState, useCallback } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  TextField, 
  Paper, 
  Alert, 
  CircularProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip
} from '@mui/material';
import { Upload as UploadIcon, Info as InfoIcon } from '@mui/icons-material';
import { DocxPreviewEditor } from './DocxPreviewEditor';
import { AgentProgressStep } from './AgentProgressStep';
import { logger } from '../utils/logger';

type AgentStep = "writer" | "reviewer";

export function AgentLoopRunner() {
  const [files, setFiles] = useState<File[]>([]);
  const [additionalInfo, setAdditionalInfo] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [preview, setPreview] = useState('');
  const [feedback, setFeedback] = useState<{score: number; suggestions: string[]}>(); 
  const [downloadUrl, setDownloadUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<AgentStep>("writer");
  const [currentLoop, setCurrentLoop] = useState(0);
  const totalLoops = 3;

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setPreview('');
    setFeedback(undefined);
    setDownloadUrl('');
    setCurrentLoop(1);
    setCurrentStep("writer");

    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));
      formData.append('additionalInfo', additionalInfo);

      logger.info('Submitting files for analysis:', files.map(f => f.name));

      const response = await fetch('/api/agent-loop', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to generate report');
      }

      const data = await response.json();
      
      if (!data.draft || typeof data.draft !== 'string') {
        throw new Error('Invalid response format: missing draft content');
      }

      setPreview(data.draft);
      setFeedback(data.feedback);
      setDownloadUrl(data.downloadUrl);
      setCurrentLoop(data.iterations);
      setCurrentStep("reviewer"); // Set to reviewer since we're showing final feedback

      logger.info('Report generated successfully');

    } catch (error) {
      logger.error('Error generating report:', error);
      setError(error instanceof Error ? error.message : 'Failed to generate report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [files, additionalInfo]);

  const isFinal = currentLoop === totalLoops || (feedback?.score || 0) > 0.9;

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 800, mx: 'auto' }}>
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Carica Documenti
        </Typography>

        <Box sx={{ mb: 3 }}>
          <Button
            variant="outlined"
            component="label"
            startIcon={<UploadIcon />}
            sx={{ mb: 1 }}
          >
            Seleziona File
            <input
              type="file"
              multiple
              hidden
              onChange={e => setFiles(Array.from(e.target.files || []))}
              accept=".doc,.docx,.txt,.pdf"
            />
          </Button>
          {files.length > 0 && (
            <List dense>
              {Array.from(files).map((file, i) => (
                <ListItem key={i}>
                  <ListItemIcon>
                    <InfoIcon color="info" />
                  </ListItemIcon>
                  <ListItemText 
                    primary={file.name}
                    secondary={`${(file.size / 1024).toFixed(1)} KB`}
                  />
                </ListItem>
              ))}
            </List>
          )}
        </Box>

        <TextField
          fullWidth
          multiline
          rows={4}
          label="Informazioni Aggiuntive"
          value={additionalInfo}
          onChange={e => setAdditionalInfo(e.target.value)}
          sx={{ mb: 3 }}
        />

        <Button
          type="submit"
          variant="contained"
          disabled={isLoading || files.length === 0}
          sx={{ minWidth: 200 }}
        >
          {isLoading ? (
            <>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              Generazione...
            </>
          ) : (
            'Genera Report'
          )}
        </Button>
      </Paper>

      {isLoading && currentLoop > 0 && (
        <AgentProgressStep
          step={currentStep}
          loop={currentLoop}
          totalLoops={totalLoops}
          feedback={feedback}
          isFinal={isFinal}
        />
      )}

      {preview && !isLoading && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ flex: 1 }}>
              Anteprima Report
            </Typography>
            <Chip
              icon={<InfoIcon />}
              label={`${currentLoop} iterazioni AI`}
              color={isFinal ? "success" : "primary"}
              variant="outlined"
              size="small"
            />
          </Box>
          <DocxPreviewEditor
            initialContent={preview}
            downloadUrl={downloadUrl}
          />
        </Paper>
      )}

      {feedback && !isLoading && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Feedback AI
          </Typography>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1">
              Punteggio: {(feedback.score * 100).toFixed(0)}%
            </Typography>
          </Box>
          {feedback.suggestions.length > 0 && (
            <List>
              {feedback.suggestions.map((suggestion, i) => (
                <ListItem key={i}>
                  <ListItemIcon>
                    <InfoIcon color="info" />
                  </ListItemIcon>
                  <ListItemText primary={suggestion} />
                </ListItem>
              ))}
            </List>
          )}
        </Paper>
      )}
    </Box>
  );
} 