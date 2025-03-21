import React, { useState, useCallback } from 'react';
import { 
  Box, 
  Button, 
  TextField, 
  Typography, 
  Paper, 
  CircularProgress,
  Alert,
  Divider
} from '@mui/material';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { 
  setLoading, 
  setContent, 
  setError,
  setActiveStep
} from '../store/reportSlice';
import { config } from '../../config';

export default function ReportEditor() {
  const dispatch = useAppDispatch();
  
  // Get state from Redux
  const reportId = useAppSelector(state => state.report.reportId);
  const content = useAppSelector(state => state.report.content);
  const loading = useAppSelector(state => state.report.loading);
  const error = useAppSelector(state => state.report.error);
  const activeStep = useAppSelector(state => state.report.activeStep);
  
  // Local state for editing
  const [editedContent, setEditedContent] = useState(content || '');
  const [refineInstructions, setRefineInstructions] = useState('');
  
  // Handle content change
  const handleContentChange = useCallback((e) => {
    setEditedContent(e.target.value);
  }, []);
  
  // Save manual edits
  const handleSaveEdits = async () => {
    if (!reportId) {
      dispatch(setError('No report ID available. Cannot save edits.'));
      return;
    }
    
    try {
      dispatch(setLoading({
        isLoading: true,
        stage: 'saving',
        message: 'Saving edits...'
      }));
      
      // Call the API to save edits
      const response = await fetch(`/api/edit/${reportId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: editedContent,
          is_finalized: false
        })
      });
      
      const data = await response.json();
      
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || `Failed to save edits: ${response.status}`);
      }
      
      // Update the content in Redux store
      dispatch(setContent(editedContent));
      
      // Complete loading
      dispatch(setLoading({
        isLoading: false,
        message: 'Edits saved successfully'
      }));
      
    } catch (err) {
      console.error('Error saving edits:', err);
      dispatch(setError(err.message || 'Failed to save edits'));
      dispatch(setLoading({
        isLoading: false,
        stage: 'error'
      }));
    }
  };
  
  // AI refinement
  const handleAIRefine = async () => {
    if (!reportId) {
      dispatch(setError('No report ID available. Cannot refine report.'));
      return;
    }
    
    if (!refineInstructions.trim()) {
      dispatch(setError('Please provide instructions for AI refinement.'));
      return;
    }
    
    try {
      dispatch(setLoading({
        isLoading: true,
        stage: 'refining',
        message: 'Refining report with AI...'
      }));
      
      // Call the API to refine the report
      const response = await fetch(`${config.API_URL}/api/edit/ai-refine`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          report_id: reportId,
          instructions: refineInstructions
        })
      });
      
      const data = await response.json();
      
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || `Failed to refine report: ${response.status}`);
      }
      
      // Process the successful response
      const refinedContent = data.data?.content || '';
      
      // Update the content in Redux store and local state
      dispatch(setContent(refinedContent));
      setEditedContent(refinedContent);
      
      // Clear the instructions
      setRefineInstructions('');
      
      // Complete loading
      dispatch(setLoading({
        isLoading: false,
        message: 'Report refined successfully'
      }));
      
    } catch (err) {
      console.error('Error refining report:', err);
      dispatch(setError(err.message || 'Failed to refine report'));
      dispatch(setLoading({
        isLoading: false,
        stage: 'error'
      }));
    }
  };
  
  // Handle continue to next step
  const handleContinue = () => {
    // Save edits one final time
    handleSaveEdits().then(() => {
      dispatch(setActiveStep(activeStep + 1));
    });
  };
  
  if (!content) {
    return (
      <Paper elevation={2} sx={{ p: 3, mt: 2 }}>
        <Alert severity="warning">
          No report content available. Please generate a report first.
        </Alert>
      </Paper>
    );
  }
  
  return (
    <Paper elevation={2} sx={{ p: 3, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Edit & Refine Report
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <TextField
        fullWidth
        label="Report Content"
        multiline
        rows={15}
        value={editedContent}
        onChange={handleContentChange}
        disabled={loading.isLoading}
        margin="normal"
        variant="outlined"
        sx={{ mb: 2, fontFamily: 'monospace' }}
      />
      
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 3 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSaveEdits}
          disabled={loading.isLoading || !reportId}
          sx={{ mr: 1 }}
        >
          {loading.isLoading && loading.stage === 'saving' ? (
            <CircularProgress size={24} sx={{ mr: 1, color: 'white' }} />
          ) : null}
          Save Edits
        </Button>
      </Box>
      
      <Divider sx={{ my: 3 }} />
      
      <Typography variant="h6" gutterBottom>
        AI Refinement
      </Typography>
      
      <TextField
        fullWidth
        label="Refinement Instructions"
        placeholder="Provide instructions for AI refinement, e.g., 'Make the report more formal' or 'Add more details about damages'"
        multiline
        rows={3}
        value={refineInstructions}
        onChange={(e) => setRefineInstructions(e.target.value)}
        disabled={loading.isLoading}
        margin="normal"
        variant="outlined"
      />
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
        <Button
          variant="outlined"
          color="primary"
          onClick={handleAIRefine}
          disabled={loading.isLoading || !reportId || !refineInstructions.trim()}
        >
          {loading.isLoading && loading.stage === 'refining' ? (
            <CircularProgress size={24} sx={{ mr: 1 }} />
          ) : null}
          Refine with AI
        </Button>
        
        <Button
          variant="contained"
          color="primary"
          onClick={handleContinue}
          disabled={loading.isLoading || !reportId}
        >
          Continue to Download
        </Button>
      </Box>
    </Paper>
  );
} 