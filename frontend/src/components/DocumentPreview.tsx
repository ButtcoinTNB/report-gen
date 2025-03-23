import React, { useState, useRef, useEffect } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  IconButton, 
  Tooltip,
  Divider,
  Pagination,
  CircularProgress,
  Skeleton,
  Alert,
  useTheme,
  useMediaQuery,
  Button
} from '@mui/material';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import PrintIcon from '@mui/icons-material/Print';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import { isBrowser } from '../utils/environment';

interface DocumentPreviewProps {
  previewUrl?: string;
  title?: string;
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

/**
 * A high-fidelity document preview component with print layout view and navigation controls
 */
const DocumentPreview: React.FC<DocumentPreviewProps> = ({
  previewUrl,
  title = 'Report Preview',
  isLoading = false,
  error = null,
  onRefresh
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const previewRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState<number>(100);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isImageLoaded, setIsImageLoaded] = useState<boolean>(false);

  // Toggle fullscreen mode
  const toggleFullscreen = () => {
    if (!isBrowser) return;
    
    if (!document.fullscreenElement) {
      if (previewRef.current?.requestFullscreen) {
        previewRef.current.requestFullscreen()
          .then(() => setIsFullscreen(true))
          .catch(err => console.error(`Error attempting to enable fullscreen: ${err.message}`));
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen()
          .then(() => setIsFullscreen(false))
          .catch(err => console.error(`Error attempting to exit fullscreen: ${err.message}`));
      }
    }
  };

  // Listen for fullscreen change events
  useEffect(() => {
    if (!isBrowser) return;

    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Increase zoom level
  const zoomIn = () => {
    setZoom(prev => Math.min(prev + 10, 200));
  };

  // Decrease zoom level
  const zoomOut = () => {
    setZoom(prev => Math.max(prev - 10, 50));
  };

  // Navigate to previous page
  const prevPage = () => {
    setPage(prev => Math.max(prev - 1, 1));
  };

  // Navigate to next page
  const nextPage = () => {
    setPage(prev => Math.min(prev + 1, totalPages));
  };

  // Handle page change
  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  // Print preview
  const handlePrint = () => {
    if (!isBrowser) return;
    
    const printWindow = window.open(previewUrl, '_blank');
    if (printWindow) {
      printWindow.onload = () => {
        printWindow.print();
      };
    }
  };

  // Mock detection of total pages (in a real implementation, this would come from the backend)
  useEffect(() => {
    if (previewUrl) {
      // Simulate fetching document metadata (in reality, this would be an API call)
      const mockFetchMetadata = () => {
        setTimeout(() => {
          // Mock response - in a real implementation, get this from the document metadata
          setTotalPages(Math.floor(Math.random() * 5) + 1);
        }, 1000);
      };
      
      mockFetchMetadata();
    }
  }, [previewUrl]);

  // Handle image load
  const handleImageLoad = () => {
    setIsImageLoaded(true);
  };

  return (
    <Paper 
      elevation={3} 
      sx={{ 
        p: 2, 
        my: 2, 
        bgcolor: 'background.paper',
        height: isFullscreen ? '100vh' : 'auto',
        display: 'flex',
        flexDirection: 'column'
      }}
      ref={previewRef}
    >
      {/* Preview header with title and controls */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        mb: 2
      }}>
        <Typography variant="h6" component="h2">
          {title}
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          {/* Zoom controls */}
          <Tooltip title="Zoom out">
            <IconButton onClick={zoomOut} size="small" disabled={zoom <= 50}>
              <ZoomOutIcon />
            </IconButton>
          </Tooltip>
          
          <Typography variant="body2" sx={{ mx: 1 }}>
            {zoom}%
          </Typography>
          
          <Tooltip title="Zoom in">
            <IconButton onClick={zoomIn} size="small" disabled={zoom >= 200}>
              <ZoomInIcon />
            </IconButton>
          </Tooltip>
          
          {/* Print button */}
          <Tooltip title="Print">
            <IconButton 
              onClick={handlePrint} 
              size="small" 
              disabled={!previewUrl || isLoading}
              sx={{ ml: 1 }}
            >
              <PrintIcon />
            </IconButton>
          </Tooltip>
          
          {/* Fullscreen toggle */}
          <Tooltip title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}>
            <IconButton 
              onClick={toggleFullscreen} 
              size="small"
              sx={{ ml: 1 }}
            >
              {isFullscreen ? <FullscreenExitIcon /> : <FullscreenIcon />}
            </IconButton>
          </Tooltip>
        </Box>
      </Box>
      
      <Divider sx={{ mb: 2 }} />
      
      {/* Error message */}
      {error && (
        <Alert 
          severity="error" 
          sx={{ mb: 2 }}
          action={
            onRefresh && (
              <Button color="inherit" size="small" onClick={onRefresh}>
                Retry
              </Button>
            )
          }
        >
          {error}
        </Alert>
      )}
      
      {/* Preview content */}
      <Box 
        sx={{ 
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: theme.palette.grey[100],
          borderRadius: 1,
          p: 2,
          overflow: 'auto',
          minHeight: isFullscreen ? 'calc(100vh - 140px)' : '500px'
        }}
      >
        {isLoading ? (
          // Loading skeleton
          <Box sx={{ width: '100%', maxWidth: '210mm', mx: 'auto' }}>
            <Skeleton variant="rectangular" width="100%" height={isFullscreen ? '80vh' : '500px'} />
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
              <CircularProgress size={24} sx={{ mr: 1 }} />
              <Typography>Loading preview...</Typography>
            </Box>
          </Box>
        ) : previewUrl ? (
          // Document preview
          <>
            {!isImageLoaded && (
              <Box sx={{ position: 'absolute', zIndex: 1 }}>
                <CircularProgress />
              </Box>
            )}
            <Box 
              sx={{ 
                width: `${zoom}%`, 
                maxWidth: zoom > 100 ? 'none' : '210mm',
                boxShadow: 3,
                transition: 'width 0.3s ease',
                background: 'white',
                border: `1px solid ${theme.palette.grey[300]}`
              }}
            >
              <img 
                src={`${previewUrl}?page=${page}`} 
                alt={`Document preview page ${page}`}
                style={{ 
                  width: '100%', 
                  height: 'auto',
                  display: isImageLoaded ? 'block' : 'none'
                }}
                onLoad={handleImageLoad}
              />
            </Box>
          </>
        ) : (
          // No preview available
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No preview available.
            </Typography>
            {onRefresh && (
              <Button 
                variant="outlined" 
                color="primary" 
                onClick={onRefresh}
                sx={{ mt: 2 }}
              >
                Generate Preview
              </Button>
            )}
          </Box>
        )}
      </Box>
      
      {/* Page navigation */}
      {previewUrl && totalPages > 1 && (
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center',
          mt: 2,
          p: 1,
          backgroundColor: theme.palette.background.paper
        }}>
          <IconButton onClick={prevPage} disabled={page <= 1}>
            <NavigateBeforeIcon />
          </IconButton>
          
          {!isMobile ? (
            <Pagination 
              count={totalPages} 
              page={page} 
              onChange={handlePageChange}
              sx={{ mx: 2 }}
              color="primary"
            />
          ) : (
            <Typography variant="body2" sx={{ mx: 2 }}>
              Page {page} of {totalPages}
            </Typography>
          )}
          
          <IconButton onClick={nextPage} disabled={page >= totalPages}>
            <NavigateNextIcon />
          </IconButton>
        </Box>
      )}
    </Paper>
  );
};

export default DocumentPreview; 