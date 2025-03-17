import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Paper,
  CircularProgress, 
  Alert,
  Divider
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { generateReport } from '../api/generate';

// Get API URL from environment or fallback to localhost
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ReportGeneratorProps {
  reportId: number | null;
  onGenerateSuccess: (text: string) => void;
}

const ReportGenerator: React.FC<ReportGeneratorProps> = ({ 
  reportId, 
  onGenerateSuccess 
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!reportId) {
      setError('No document has been uploaded');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await generateReport(reportId);

      if (response) {
        // If there was an error in API but it returned fallback content
        if (response.error) {
          setError('An error occurred during generation, but partial content was returned.');
        }
        
        // Use the content from the response
        if (response.content) {
          onGenerateSuccess(response.content);
        } else if (response.output) {
          onGenerateSuccess(response.output);
        } else {
          throw new Error('No content returned from generation API');
        }
      } else {
        throw new Error('Failed to generate report content');
      }
    } catch (err) {
      console.error('Error generating report:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate report. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h5" gutterBottom>
        AI Report Generation
      </Typography>
      
      <Divider sx={{ my: 2 }} />
      
      <Box sx={{ mb: 2 }}>
        <Typography variant="body1" paragraph>
          Click the button below to analyze your uploaded documents and generate a 
          professional insurance report using AI.
        </Typography>
      </Box>
      
      <Button
        variant="contained"
        color="secondary"
        size="large"
        onClick={handleGenerate}
        disabled={loading || !reportId}
        startIcon={loading ? (
          <CircularProgress size={20} color="inherit" />
        ) : (
          <AutoAwesomeIcon />
        )}
        fullWidth
        sx={{ mb: 2 }}
      >
        {loading ? 'Generating Report...' : 'Generate AI Report'}
      </Button>
      
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Paper>
  );
};

export default ReportGenerator; 