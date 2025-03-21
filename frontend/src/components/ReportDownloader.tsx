import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Paper,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  CardActions,
  Divider,
  Grid
} from '@mui/material';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { setLoading, setError, setPreviewUrl } from '../store/reportSlice';
import DownloadIcon from '@mui/icons-material/Download';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import DescriptionIcon from '@mui/icons-material/Description';
import PreviewIcon from '@mui/icons-material/Preview';
import { config } from '../../config';

const ReportDownloader: React.FC = () => {
  const dispatch = useAppDispatch();
  const [previewGenerated, setPreviewGenerated] = useState<boolean>(false);
  
  // Get state from Redux
  const reportId = useAppSelector(state => state.report.reportId);
  const loading = useAppSelector(state => state.report.loading);
  const error = useAppSelector(state => state.report.error);
  const previewUrl = useAppSelector(state => state.report.previewUrl);
  
  // Generate preview
  const handleGeneratePreview = async (): Promise<void> => {
    if (!reportId) {
      dispatch(setError('No report ID available. Cannot generate preview.'));
      return;
    }
    
    try {
      dispatch(setLoading({
        isLoading: true,
        stage: 'preview',
        message: 'Generating preview...'
      }));
      
      // Call the API to generate preview
      const response = await fetch(`${config.API_URL}/api/format/preview-file`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          report_id: reportId
        })
      });
      
      const data = await response.json();
      
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || `Failed to generate preview: ${response.status}`);
      }
      
      // Get the preview URL
      const previewId = data.data?.preview_id;
      if (!previewId) {
        throw new Error('No preview ID received from server');
      }
      
      const url = `/api/format/preview-file/${previewId}`;
      
      // Store preview URL
      dispatch(setPreviewUrl(url));
      setPreviewGenerated(true);
      
      // Complete loading
      dispatch(setLoading({
        isLoading: false,
        message: 'Preview generated successfully'
      }));
      
    } catch (err) {
      console.error('Error generating preview:', err);
      dispatch(setError(err instanceof Error ? err.message : 'Failed to generate preview'));
      dispatch(setLoading({
        isLoading: false,
        stage: 'error'
      }));
    }
  };
  
  // Format final report
  const handleFormatReport = async (format: string = 'docx'): Promise<void> => {
    if (!reportId) {
      dispatch(setError('No report ID available. Cannot format report.'));
      return;
    }
    
    try {
      dispatch(setLoading({
        isLoading: true,
        stage: 'formatting',
        message: `Formatting report as ${format.toUpperCase()}...`
      }));
      
      // Call the API to format report
      const response = await fetch(`${config.API_URL}/api/format/final`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          report_id: reportId
        })
      });
      
      const data = await response.json();
      
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || `Failed to format report: ${response.status}`);
      }
      
      // Get the download URL
      const downloadUrl = data.data?.download_url;
      if (!downloadUrl) {
        throw new Error('No download URL received from server');
      }
      
      // Complete loading
      dispatch(setLoading({
        isLoading: false,
        message: 'Report formatted successfully'
      }));
      
      // Trigger download
      window.location.href = downloadUrl;
      
    } catch (err) {
      console.error('Error formatting report:', err);
      dispatch(setError(err instanceof Error ? err.message : 'Failed to format report'));
      dispatch(setLoading({
        isLoading: false,
        stage: 'error'
      }));
    }
  };
  
  // Download report
  const handleDownload = async (format: string = 'docx'): Promise<void> => {
    if (!reportId) {
      dispatch(setError('No report ID available. Cannot download report.'));
      return;
    }
    
    try {
      dispatch(setLoading({
        isLoading: true,
        stage: 'downloading',
        message: `Preparing ${format.toUpperCase()} download...`
      }));
      
      // URL for download - this is a direct download
      const downloadUrl = `/api/download/${format === 'docx' ? 'docx/' : ''}${reportId}`;
      
      // Complete loading
      dispatch(setLoading({
        isLoading: false
      }));
      
      // Trigger download
      window.location.href = downloadUrl;
      
    } catch (err) {
      console.error('Error downloading report:', err);
      dispatch(setError(err instanceof Error ? err.message : 'Failed to download report'));
      dispatch(setLoading({
        isLoading: false,
        stage: 'error'
      }));
    }
  };
  
  if (!reportId) {
    return (
      <Paper elevation={2} sx={{ p: 3, mt: 2 }}>
        <Alert severity="warning">
          No report available. Please generate a report first.
        </Alert>
      </Paper>
    );
  }
  
  return (
    <Paper elevation={2} sx={{ p: 3, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Download Report
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {loading.isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <CircularProgress size={24} sx={{ mr: 1 }} />
          <Typography>{loading.message || 'Processing...'}</Typography>
        </Box>
      )}
      
      <Grid container spacing={3} sx={{ mt: 1 }}>
        {/* Preview Card */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
                <PreviewIcon sx={{ mr: 1 }} />
                Preview Report
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Generate a preview of your report to see how it will look before downloading the final version.
              </Typography>
            </CardContent>
            <CardActions>
              <Button 
                startIcon={<PreviewIcon />}
                onClick={handleGeneratePreview}
                disabled={loading.isLoading}
                variant="contained"
                color="primary"
                fullWidth
              >
                Generate Preview
              </Button>
            </CardActions>
            {previewGenerated && previewUrl && (
              <CardActions>
                <Button 
                  component="a"
                  href={previewUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="outlined"
                  fullWidth
                >
                  Open Preview
                </Button>
              </CardActions>
            )}
          </Card>
        </Grid>
        
        {/* DOCX Download Card */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
                <DescriptionIcon sx={{ mr: 1 }} />
                DOCX Format
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Download the report as a DOCX file for editing in Microsoft Word or other word processors.
              </Typography>
            </CardContent>
            <CardActions>
              <Button 
                startIcon={<DownloadIcon />}
                onClick={() => handleDownload('docx')}
                disabled={loading.isLoading}
                variant="contained"
                color="primary"
                fullWidth
              >
                Download DOCX
              </Button>
            </CardActions>
          </Card>
        </Grid>
        
        {/* PDF Download Card */}
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
                <PictureAsPdfIcon sx={{ mr: 1 }} />
                PDF Format
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Download the report as a PDF file for viewing on any device with consistent formatting.
              </Typography>
            </CardContent>
            <CardActions>
              <Button 
                startIcon={<DownloadIcon />}
                onClick={() => handleFormatReport('pdf')}
                disabled={loading.isLoading}
                variant="contained"
                color="primary"
                fullWidth
              >
                Download PDF
              </Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default ReportDownloader; 