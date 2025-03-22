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

interface AgentLoopRunnerProps {
  reportId: string;
  onComplete: (result: { previewUrl?: string }) => void;
}

export function AgentLoopRunner({ reportId, onComplete }: AgentLoopRunnerProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [additionalInfo, setAdditionalInfo] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [preview, setPreview] = useState('');
  const [feedback, setFeedback] = useState<{score: number; suggestions: string[]}>();
  const [downloadUrl, setDownloadUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<AgentStep>("writer");
  const [currentLoop, setCurrentLoop] = useState(0);
  const [totalIterations, setTotalIterations] = useState(0);
  const [refinementCount, setRefinementCount] = useState(0);
  const [analysis, setAnalysis] = useState<{
    findings: Record<string, any>;
    suggestions: string[];
    extracted_variables: Record<string, any>;
  } | null>(null);
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
    setTotalIterations(0);
    setRefinementCount(0);

    try {
      if (!files.length) {
        throw new Error('Please select at least one file to analyze');
      }

      logger.info('Submitting files for analysis:', files.map(f => f.name));

      const formData = new FormData();
      files.forEach(file => formData.append('files', file));
      formData.append('additional_info', additionalInfo);
      formData.append('report_id', reportId);

      setCurrentStep("writer");
      logger.info('Uploading files...');
      
      const response = await fetch('/api/upload/files', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to upload files');
      }

      const uploadData = await response.json();
      logger.info('Files uploaded successfully, starting agent loop...');

      // Start the agent loop
      setCurrentStep("writer");
      const agentResponse = await fetch('/api/agent-loop/generate-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          report_id: reportId,
          additional_info: additionalInfo
        })
      });

      if (!agentResponse.ok) {
        const errorData = await agentResponse.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to generate report');
      }

      const agentData = await agentResponse.json();
      
      if (!agentData.draft) {
        throw new Error('Invalid response format: missing draft content');
      }

      setPreview(agentData.draft);
      setFeedback(agentData.feedback);
      setDownloadUrl(agentData.docx_url || '');
      setCurrentLoop(agentData.iterations);
      setTotalIterations(agentData.iterations);
      setCurrentStep("reviewer");

      // Call onComplete with the result
      onComplete({ previewUrl: agentData.docx_url });

      logger.info('Report generated successfully after', agentData.iterations, 'iterations');

    } catch (error) {
      logger.error('Error generating report:', error);
      setError(error instanceof Error ? error.message : 'Failed to generate report. Please try again.');
      setCurrentStep("writer");
    } finally {
      setIsLoading(false);
    }
  }, [files, additionalInfo, onComplete, reportId]);

  // Handler for refinement completion (to track refinements)
  const handleRefinementComplete = useCallback((data: { draft: string, feedback: {score: number; suggestions: string[]}, iterations: number, docx_url?: string }) => {
    setPreview(data.draft);
    setFeedback(data.feedback);
    if (data.docx_url) {
      setDownloadUrl(data.docx_url);
    }
    setRefinementCount(prev => prev + 1);
    setTotalIterations(prev => prev + data.iterations);
  }, []);

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
              accept=".doc,.docx,.pdf,.txt,.jpg,.jpeg,.png,.gif,.bmp,.webp,.tiff,.rtf,.odt,.csv,.md,.html,.xls,.xlsx"
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

        {analysis && (
          <>
            <Typography variant="subtitle1" gutterBottom>
              Analisi Documenti
            </Typography>
            <List dense sx={{ mb: 3 }}>
              {analysis.suggestions.map((suggestion, i) => (
                <ListItem key={i}>
                  <ListItemIcon>
                    <InfoIcon color="info" />
                  </ListItemIcon>
                  <ListItemText primary={suggestion} />
                </ListItem>
              ))}
            </List>
          </>
        )}

        <TextField
          fullWidth
          multiline
          rows={4}
          label="Informazioni Aggiuntive"
          value={additionalInfo}
          onChange={e => setAdditionalInfo(e.target.value)}
          sx={{ mb: 3 }}
          helperText="Fornisci informazioni aggiuntive per migliorare il report"
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
              {currentStep === "writer" ? "Scrittura..." : "Revisione..."}
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
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip
                icon={<InfoIcon />}
                label={`${currentLoop} iterazioni iniziali`}
                color={isFinal ? "success" : "primary"}
                variant="outlined"
                size="small"
              />
              {refinementCount > 0 && (
                <Chip
                  icon={<InfoIcon />}
                  label={`${refinementCount} raffinamenti`}
                  color="secondary"
                  variant="outlined"
                  size="small"
                />
              )}
              {totalIterations > currentLoop && (
                <Chip
                  icon={<InfoIcon />}
                  label={`${totalIterations} iterazioni totali`}
                  color="info"
                  variant="outlined"
                  size="small"
                />
              )}
            </Box>
          </Box>
          <DocxPreviewEditor
            initialContent={preview}
            downloadUrl={downloadUrl}
            reportId={reportId}
            showRefinementOptions={!isLoading && currentLoop > 0}
            onRefinementComplete={handleRefinementComplete}
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