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
  Stack,
  Card,
  CardContent,
  CardActions,
  Tooltip,
  IconButton
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import DescriptionIcon from '@mui/icons-material/Description';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { downloadApi } from '../src/services';
import PDFPreview from './PDFPreview';

interface DownloadReportProps {
  reportId: string | null;
  isPdfReady: boolean;
}

const DownloadReport: React.FC<DownloadReportProps> = ({
  reportId,
  isPdfReady
}) => {
  const [loading, setLoading] = useState(false);
  const [docxLoading, setDocxLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const handlePdfDownload = async () => {
    if (!reportId) {
      setError('No report ID provided');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Use the new TypeScript API service
      const pdfBlob = await downloadApi.downloadReport(reportId, 'docx');
      
      // Create a download link
      const url = window.URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${reportId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      // Clean up the URL object
      window.URL.revokeObjectURL(url);
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
      // Use the new TypeScript API service
      downloadApi.downloadToDevice(reportId, `report_${reportId}.docx`, 'docx');
    } catch (err) {
      console.error('Error downloading DOCX report:', err);
      setError(err instanceof Error ? err.message : 'Failed to download the DOCX report. Please try again.');
    } finally {
      setDocxLoading(false);
    }
  };

  const handlePreviewOpen = () => {
    setShowPreview(true);
  };

  const handlePreviewClose = () => {
    setShowPreview(false);
  };

  return (
    <>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Download Report
        </Typography>
        
        <Divider sx={{ my: 2 }} />
        
        <Box sx={{ mb: 3 }}>
          <Typography variant="body1" paragraph>
            {isPdfReady
              ? 'Your report has been finalized and is ready for download.'
              : 'Please finalize your report before downloading.'}
          </Typography>
          
          {isPdfReady && (
            <Typography variant="body2" color="text.secondary">
              Preview your report before downloading or choose your preferred format.
            </Typography>
          )}
        </Box>
        
        {isPdfReady && (
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <PictureAsPdfIcon color="error" sx={{ mr: 1 }} />
                    <Typography variant="h6">PDF Format</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Standard PDF format with professional formatting, ideal for printing or sharing.
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button 
                    variant="contained" 
                    color="primary"
                    onClick={handlePdfDownload}
                    disabled={loading || !reportId}
                    startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <DownloadIcon />}
                    fullWidth
                  >
                    {loading ? 'Downloading...' : 'Download PDF'}
                  </Button>
                  
                  <Tooltip title="Preview PDF">
                    <IconButton 
                      color="primary" 
                      onClick={handlePreviewOpen}
                      disabled={!reportId}
                    >
                      <VisibilityIcon />
                    </IconButton>
                  </Tooltip>
                </CardActions>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <DescriptionIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">Word Document</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Editable DOCX format, perfect for making additional changes or customizations.
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button 
                    variant="contained" 
                    color="secondary"
                    onClick={handleDocxDownload}
                    disabled={docxLoading || !reportId}
                    startIcon={docxLoading ? <CircularProgress size={20} color="inherit" /> : <DownloadIcon />}
                    fullWidth
                  >
                    {docxLoading ? 'Downloading...' : 'Download DOCX'}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          </Grid>
        )}
        
        {!isPdfReady && (
          <Alert severity="info" sx={{ mb: 3 }}>
            You need to finalize your report before downloading. Click the "Finalize Report" button in the Report Preview section.
          </Alert>
        )}
        
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Paper>
      
      {showPreview && reportId && (
        <PDFPreview 
          reportId={reportId} 
          onClose={handlePreviewClose} 
        />
      )}
    </>
  );
};

export default DownloadReport; 