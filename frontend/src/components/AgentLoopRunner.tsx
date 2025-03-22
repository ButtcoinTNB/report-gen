"use client";

import { useState, useCallback, useEffect } from 'react';
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
import { AgentInitializationTracker } from './index';
import { logger } from '../utils/logger';
import { reportService } from '../services/api/ReportService';
import { apiConfig } from '../config/api.config';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { 
  initAgentLoop, 
  updateAgentLoopProgress, 
  completeAgentLoop, 
  failAgentLoop, 
  setError, 
  setPreviewUrl, 
  setContent
} from '../store/reportSlice';

type AgentStep = "writer" | "reviewer";

interface AgentLoopRunnerProps {
  reportId: string;
  onComplete: (result: { previewUrl?: string }) => void;
}

export function AgentLoopRunner({ reportId, onComplete }: AgentLoopRunnerProps) {
  const dispatch = useAppDispatch();
  const { additionalInfo, agentLoop, documentIds } = useAppSelector(state => state.report);
  const [files, setFiles] = useState<File[]>([]);
  const [localAdditionalInfo, setLocalAdditionalInfo] = useState('');
  const [feedback, setFeedback] = useState<{score: number; suggestions: string[]}>();
  const [refinementCount, setRefinementCount] = useState(0);
  
  // Initialize local state from Redux store
  useEffect(() => {
    setLocalAdditionalInfo(additionalInfo);
  }, [additionalInfo]);
  
  // Handle starting the agent loop
  const handleStartAgentLoop = useCallback(async () => {
    // Validate inputs
    if (documentIds.length === 0 && files.length === 0) {
      dispatch(setError('Devi caricare almeno un documento per generare il report'));
      return;
    }
    
    try {
      // Initialize agent loop in Redux
      dispatch(initAgentLoop({}));
      
      // Start agent loop initialization with progress updates
      const result = await reportService.initializeAgentLoop(
        {
          reportId,
          additionalInfo: localAdditionalInfo
        },
        (progress, message) => {
          dispatch(updateAgentLoopProgress({ progress, message }));
        }
      );
      
      // Update feedback state
      setFeedback(result.feedback);
      
      // Complete the agent loop with the result
      dispatch(completeAgentLoop({
        content: result.draft,
        previewUrl: result.docxUrl,
        iterations: result.iterations
      }));
      
      // Notify parent component about completion
      onComplete({ previewUrl: result.docxUrl });
      
      logger.info('Report generated successfully after', result.iterations, 'iterations');
    } catch (error) {
      logger.error('Error generating report:', error);
      
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate report. Please try again.';
      dispatch(failAgentLoop(errorMessage));
      dispatch(setError(errorMessage));
    }
  }, [dispatch, reportId, localAdditionalInfo, documentIds, files, onComplete]);
  
  // Handle file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };
  
  // Handle manual file upload (for documents that haven't been uploaded via the FileUploader)
  const handleUploadFiles = async () => {
    if (!files.length) return;
    
    try {
      dispatch(updateAgentLoopProgress({ 
        progress: 5, 
        message: 'Caricamento documenti in corso...' 
      }));
      
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));
      formData.append('report_id', reportId);
      
      const response = await fetch(apiConfig.endpoints.fileUpload, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to upload files');
      }
      
      // Continue with agent loop after files are uploaded
      handleStartAgentLoop();
    } catch (error) {
      logger.error('Error uploading files:', error);
      
      const errorMessage = error instanceof Error ? error.message : 'Failed to upload files. Please try again.';
      dispatch(failAgentLoop(errorMessage));
      dispatch(setError(errorMessage));
    }
  };
  
  // Handle submit - start the agent loop
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    // If there are new files to upload, handle that first
    if (files.length > 0) {
      await handleUploadFiles();
    } else {
      // Otherwise, just start the agent loop with existing documents
      await handleStartAgentLoop();
    }
  }, [files, handleStartAgentLoop, handleUploadFiles]);

  // Handler for refinement completion (to track refinements)
  const handleRefinementComplete = useCallback((data: { draft: string, feedback: {score: number; suggestions: string[]}, iterations: number, docx_url?: string }) => {
    dispatch(setContent(data.draft));
    setFeedback(data.feedback);
    
    if (data.docx_url) {
      dispatch(setPreviewUrl(data.docx_url));
    }
    
    setRefinementCount(prev => prev + 1);
    
    // Update agent loop state
    dispatch(completeAgentLoop({
      content: data.draft,
      previewUrl: data.docx_url,
      iterations: data.iterations
    }));
  }, [dispatch]);
  
  // Show either the agent initialization/progress tracker or the form to start
  const showAgentTracker = agentLoop.isInitializing || 
                          agentLoop.isRunning || 
                          agentLoop.stage === 'error' ||
                          agentLoop.progress > 0;

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 800, mx: 'auto' }}>
      {/* Error handling at the top level */}
      {agentLoop.error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {agentLoop.error}
        </Alert>
      )}

      {/* Agent Initialization Tracker */}
      {showAgentTracker && (
        <AgentInitializationTracker />
      )}

      {/* Input form - hidden when agent is running */}
      {!agentLoop.isInitializing && !agentLoop.isRunning && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Generazione Report
          </Typography>

          {documentIds.length === 0 && (
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
                  onChange={handleFileChange}
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
          )}

          {documentIds.length > 0 && (
            <Alert severity="info" sx={{ mb: 3 }}>
              {documentIds.length} documenti caricati e pronti per l'elaborazione
            </Alert>
          )}

          <TextField
            fullWidth
            multiline
            rows={4}
            label="Informazioni Aggiuntive"
            value={localAdditionalInfo}
            onChange={e => setLocalAdditionalInfo(e.target.value)}
            sx={{ mb: 3 }}
            helperText="Fornisci informazioni aggiuntive per migliorare il report"
          />

          <Button
            type="submit"
            variant="contained"
            disabled={agentLoop.isInitializing || agentLoop.isRunning || (documentIds.length === 0 && files.length === 0)}
            sx={{ minWidth: 200 }}
          >
            Genera Report
          </Button>
        </Paper>
      )}

      {/* Show iteration feedback when appropriate */}
      {agentLoop.isRunning && agentLoop.stage !== 'initializing' && (
        <AgentProgressStep
          step={agentLoop.stage === 'writing' ? 'writer' : 'reviewer'}
          loop={agentLoop.currentIteration}
          totalLoops={agentLoop.totalIterations}
          feedback={feedback}
          isFinal={agentLoop.stage === 'complete'}
        />
      )}

      {/* Preview content when agent loop is complete */}
      {agentLoop.stage === 'complete' && (
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Anteprima Report
          </Typography>
          
          {feedback && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1">
                Qualità del report: {Math.round(feedback.score * 100)}%
              </Typography>
              
              {feedback.suggestions.length > 0 && (
                <List dense>
                  {feedback.suggestions.map((suggestion, i) => (
                    <ListItem key={i}>
                      <ListItemIcon>
                        <InfoIcon color="info" fontSize="small" />
                      </ListItemIcon>
                      <ListItemText 
                        primary={suggestion} 
                        primaryTypographyProps={{ variant: 'body2' }}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </Box>
          )}
        </Paper>
      )}
    </Box>
  );
} 