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
import DownloadIcon from '@mui/icons-material/Download';
import { downloadPDF } from '../api/download';

interface DownloadReportProps {
  reportId: number | null;
  isPdfReady: boolean;
}

const DownloadReport: React.FC<DownloadReportProps> = ({
  reportId,
  isPdfReady
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    if (!reportId) {
      setError('No report ID provided');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await downloadPDF(reportId);
      // Success is handled by the downloadPDF function (it triggers the browser download)
    } catch (err) {
      console.error('Error downloading report:', err);
      setError('Failed to download the report. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Download Report
      </Typography>
      
      <Divider sx={{ my: 2 }} />
      
      <Box sx={{ mb: 2 }}>
        <Typography variant="body1" paragraph>
          {isPdfReady
            ? 'Your report has been finalized and is ready for download.'
            : 'Please finalize your report before downloading.'}
        </Typography>
      </Box>
      
      <Button
        variant="contained"
        color="primary"
        onClick={handleDownload}
        disabled={loading || !reportId || !isPdfReady}
        startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <DownloadIcon />}
        fullWidth
      >
        {loading ? 'Downloading...' : 'Download PDF Report'}
      </Button>
      
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Paper>
  );
};

export default DownloadReport; 