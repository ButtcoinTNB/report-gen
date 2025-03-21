import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  TextField, 
  Typography, 
  Paper, 
  LinearProgress,
  Alert
} from '@mui/material';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { 
  setLoading, 
  setContent, 
  setError,
  setActiveStep,
  setReportId
} from '../store/reportSlice';
import { config } from '../../config';

const ReportGenerator: React.FC = () => {
  const dispatch = useAppDispatch();
  const [additionalInfo, setAdditionalInfo] = useState<string>('');
  
  // Get state from Redux
  const documentIds = useAppSelector(state => state.report.documentIds);
  const reportId = useAppSelector(state => state.report.reportId);
  const loading = useAppSelector(state => state.report.loading);
  const error = useAppSelector(state => state.report.error);
  const activeStep = useAppSelector(state => state.report.activeStep);
  
  const handleGenerateReport = async (): Promise<void> => {
    if (!documentIds || documentIds.length === 0) {
      dispatch(setError('No documents uploaded. Please upload documents first.'));
      return;
    }
    
    try {
      dispatch(setLoading({
        isLoading: true,
        stage: 'generating',
        progress: 10,
        message: 'Generating report from documents...'
      }));
      
      // Prepare the request payload
      const payload: {
        document_ids: string[];
        additional_info: string;
        report_id?: string;
      } = {
        document_ids: documentIds,
        additional_info: additionalInfo
      };
      
      // If we have a report ID already, use it
      if (reportId) {
        payload.report_id = reportId;
      }
      
      // Call the API to generate the report
      const response = await fetch(`${config.API_URL}/api/generate/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      
      // Update progress
      dispatch(setLoading({
        progress: 50,
        message: 'Processing content...'
      }));
      
      const data = await response.json();
      
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || `Generation failed with status ${response.status}`);
      }
      
      // Process the successful response
      dispatch(setLoading({
        progress: 90,
        message: 'Finalizing report...'
      }));
      
      // Store the report content and ID
      if (data.data) {
        // Handle both snake_case and camelCase responses
        const content = data.data.content || '';
        const reportIdFromResponse = data.data.report_id || data.data.reportId;
        
        // Store report content
        if (content) {
          dispatch(setContent(content));
        }
        
        // Store report ID if we got one
        if (reportIdFromResponse) {
          dispatch(setReportId(reportIdFromResponse));
        }
        
        // Move to the next step after a brief delay to show completion
        setTimeout(() => {
          dispatch(setLoading({
            isLoading: false,
            progress: 100,
            stage: 'complete',
            message: 'Report generated successfully!'
          }));
          
          dispatch(setActiveStep(activeStep + 1));
        }, 500);
      } else {
        throw new Error('No data received from the server');
      }
    } catch (err) {
      console.error('Generation error:', err);
      dispatch(setError(err instanceof Error ? err.message : 'Failed to generate report'));
      dispatch(setLoading({
        isLoading: false,
        stage: 'error'
      }));
    }
  };
  
  return (
    <Paper elevation={2} sx={{ p: 3, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Generate Insurance Report
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {documentIds && documentIds.length > 0 ? (
        <Alert severity="success" sx={{ mb: 2 }}>
          {documentIds.length} document{documentIds.length !== 1 ? 's' : ''} ready for processing
        </Alert>
      ) : (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No documents uploaded yet. Please upload documents first.
        </Alert>
      )}
      
      <TextField
        fullWidth
        label="Additional Information"
        placeholder="Add any additional details or specific instructions for the report generation"
        multiline
        rows={4}
        value={additionalInfo}
        onChange={(e) => setAdditionalInfo(e.target.value)}
        disabled={loading.isLoading}
        margin="normal"
        variant="outlined"
      />
      
      {loading.isLoading && (
        <Box sx={{ mt: 2, mb: 2 }}>
          <Typography variant="body2" gutterBottom>
            {loading.message || 'Processing...'}
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={loading.progress} 
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>
      )}
      
      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleGenerateReport}
          disabled={loading.isLoading || !documentIds || documentIds.length === 0}
        >
          {loading.isLoading ? 'Generating...' : 'Generate Report'}
        </Button>
      </Box>
    </Paper>
  );
};

export default ReportGenerator; 