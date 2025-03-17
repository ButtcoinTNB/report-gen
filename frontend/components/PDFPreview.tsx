import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  IconButton, 
  CircularProgress,
  Stack,
  Slider,
  Button,
  Alert
} from '@mui/material';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import CloseIcon from '@mui/icons-material/Close';
import RefreshIcon from '@mui/icons-material/Refresh';
import { fetchPDFPreview } from '../api/download';

interface PDFPreviewProps {
  reportId: number | null;
  onClose: () => void;
}

const PDFPreview: React.FC<PDFPreviewProps> = ({ reportId, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [zoom, setZoom] = useState(100);
  
  useEffect(() => {
    if (!reportId) {
      setError('No report ID provided');
      setLoading(false);
      return;
    }
    
    loadPDFPreview();
  }, [reportId]);
  
  const loadPDFPreview = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await fetchPDFPreview(reportId as number);
      if (result && result.previewUrl) {
        setPdfUrl(result.previewUrl);
      } else {
        setError('Failed to generate PDF preview');
      }
    } catch (err) {
      console.error('Error generating PDF preview:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate PDF preview. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 10, 200));
  };
  
  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 10, 50));
  };
  
  const handleZoomChange = (event: Event, newValue: number | number[]) => {
    setZoom(newValue as number);
  };
  
  const handleRefresh = () => {
    loadPDFPreview();
  };
  
  return (
    <Paper 
      elevation={3} 
      sx={{ 
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '90%',
        maxWidth: '1000px',
        height: '90vh',
        maxHeight: '800px',
        p: 2,
        zIndex: 1300,
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        mb: 2
      }}>
        <Typography variant="h6">PDF Preview</Typography>
        <IconButton onClick={onClose} aria-label="close">
          <CloseIcon />
        </IconButton>
      </Box>
      
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        mb: 2 
      }}>
        <IconButton onClick={handleZoomOut}>
          <ZoomOutIcon />
        </IconButton>
        
        <Slider
          value={zoom}
          min={50}
          max={200}
          step={10}
          onChange={handleZoomChange}
          aria-labelledby="zoom-slider"
          valueLabelDisplay="auto"
          valueLabelFormat={value => `${value}%`}
          sx={{ mx: 2, maxWidth: '200px' }}
        />
        
        <IconButton onClick={handleZoomIn}>
          <ZoomInIcon />
        </IconButton>
        
        <Typography variant="body2" sx={{ ml: 1 }}>
          {zoom}%
        </Typography>
        
        <IconButton onClick={handleRefresh} sx={{ ml: 2 }} aria-label="refresh">
          <RefreshIcon />
        </IconButton>
      </Box>
      
      <Box sx={{ 
        flexGrow: 1, 
        position: 'relative',
        overflow: 'auto',
        border: '1px solid #ddd',
        borderRadius: 1,
        backgroundColor: '#f5f5f5',
        display: 'flex',
        justifyContent: 'center'
      }}>
        {loading ? (
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            height: '100%'
          }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Box sx={{ 
            display: 'flex', 
            flexDirection: 'column',
            justifyContent: 'center', 
            alignItems: 'center',
            height: '100%',
            p: 3
          }}>
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
            <Button 
              variant="contained" 
              onClick={handleRefresh}
              startIcon={<RefreshIcon />}
            >
              Try Again
            </Button>
          </Box>
        ) : pdfUrl ? (
          <Box sx={{ 
            width: `${zoom}%`, 
            height: '100%',
            transition: 'width 0.3s ease'
          }}>
            <iframe 
              src={pdfUrl}
              style={{ 
                width: '100%', 
                height: '100%', 
                border: 'none'
              }}
              title="PDF Preview"
            />
          </Box>
        ) : (
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            height: '100%'
          }}>
            <Typography variant="body1" color="text.secondary">
              No preview available
            </Typography>
          </Box>
        )}
      </Box>
    </Paper>
  );
};

export default PDFPreview; 