import React, { useState } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Divider,
  Grid,
  Stack
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import DescriptionIcon from '@mui/icons-material/Description';
import { downloadPDF, downloadDOCX, generateDOCX } from '../api/download';

interface DownloadReportProps {
  reportId: number | null;
  isPdfReady: boolean;
}

const DownloadReport: React.FC<DownloadReportProps> = ({
  reportId,
  isPdfReady
}) => {
  const [loading, setLoading] = useState(false);
  const [docxLoading, setDocxLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePdfDownload = async () => {
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
      console.error('Error downloading PDF report:', err);
      setError(err instanceof Error ? err.message : 'Failed to download the PDF report. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDocxDownload = async () => {
    if (!reportId) {
      setError('No report ID provided');
      return;
    }

    setDocxLoading(true);
    setError(null);

    try {
      // First generate the DOCX
      await generateDOCX(reportId);
      
      // Then download it
      await downloadDOCX(reportId);
      // Success is handled by the downloadDOCX function (it triggers the browser download)
    } catch (err) {
      console.error('Error downloading DOCX report:', err);
      setError(err instanceof Error ? err.message : 'Failed to download the DOCX report. Please try again.');
    } finally {
      setDocxLoading(false);
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
      
      <Stack spacing={2}>
        <Button
          variant="contained"
          color="primary"
          onClick={handlePdfDownload}
          disabled={loading || !reportId || !isPdfReady}
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PictureAsPdfIcon />}
          fullWidth
        >
          {loading ? 'Downloading...' : 'Download PDF Report'}
        </Button>
        
        <Button
          variant="contained"
          color="secondary"
          onClick={handleDocxDownload}
          disabled={docxLoading || !reportId || !isPdfReady}
          startIcon={docxLoading ? <CircularProgress size={20} color="inherit" /> : <DescriptionIcon />}
          fullWidth
        >
          {docxLoading ? 'Downloading...' : 'Download DOCX Report'}
        </Button>
      </Stack>
      
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Paper>
  );
};

export default DownloadReport; 