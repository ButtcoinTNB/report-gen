import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  LinearProgress, 
  CircularProgress,
  Divider,
  Backdrop,
  Fade,
  Button,
  Alert,
  IconButton,
  Tooltip
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { formatBytes } from '../utils/formatters';

interface DownloadProgressTrackerProps {
  isDownloading: boolean;
  fileName?: string;
  fileSize?: number; // in bytes
  progress?: number; // 0-100
  error?: string | null;
  onClose?: () => void;
  onRetry?: () => void;
}

/**
 * A component that displays download progress for large documents
 * It shows a progress bar, file name, download speed, and estimated time remaining
 */
const DownloadProgressTracker: React.FC<DownloadProgressTrackerProps> = ({
  isDownloading,
  fileName = 'document.docx',
  fileSize = 0,
  progress = 0,
  error = null,
  onClose,
  onRetry
}) => {
  const [showTracker, setShowTracker] = useState<boolean>(false);
  const [downloadSpeed, setDownloadSpeed] = useState<number>(0); // bytes per second
  const [startTime, setStartTime] = useState<number>(0);
  const [downloadedBytes, setDownloadedBytes] = useState<number>(0);
  const [timeRemaining, setTimeRemaining] = useState<number>(0); // seconds

  // Show/hide the tracker based on download state
  useEffect(() => {
    if (isDownloading) {
      setShowTracker(true);
      setStartTime(Date.now());
      setDownloadedBytes(0);
    } else if (!error) {
      // Hide the tracker after download completes, but allow time to see 100%
      const timer = setTimeout(() => {
        setShowTracker(false);
      }, 3000);
      
      return () => clearTimeout(timer);
    }
  }, [isDownloading, error]);

  // Calculate download speed and time remaining
  useEffect(() => {
    if (isDownloading && fileSize > 0 && progress > 0) {
      // Calculate downloaded bytes
      const currentBytes = (fileSize * progress) / 100;
      setDownloadedBytes(currentBytes);
      
      // Calculate elapsed time in seconds
      const elapsedTime = (Date.now() - startTime) / 1000;
      
      // Calculate download speed in bytes per second
      const speed = currentBytes / elapsedTime;
      setDownloadSpeed(speed);
      
      // Calculate time remaining in seconds
      const bytesRemaining = fileSize - currentBytes;
      const timeRemainingSeconds = speed > 0 ? bytesRemaining / speed : 0;
      setTimeRemaining(timeRemainingSeconds);
    }
  }, [isDownloading, fileSize, progress, startTime]);

  // Format time remaining
  const formatTimeRemaining = (seconds: number): string => {
    if (seconds < 1) return 'Almost done';
    if (seconds < 60) return `${Math.round(seconds)} seconds`;
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')} minutes`;
  };

  // Handle retry
  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    }
  };

  // Don't render anything if the tracker is not visible
  if (!showTracker) {
    return null;
  }

  return (
    <Backdrop
      sx={{ 
        color: '#fff', 
        zIndex: (theme) => theme.zIndex.drawer + 1,
        bgcolor: 'rgba(0, 0, 0, 0.7)'
      }}
      open={showTracker}
    >
      <Fade in={showTracker}>
        <Paper 
          elevation={4} 
          sx={{ 
            p: 3, 
            borderRadius: 2, 
            maxWidth: 500, 
            width: '90%'
          }}
        >
          {/* Header */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" component="h2" sx={{ display: 'flex', alignItems: 'center' }}>
              <DownloadIcon sx={{ mr: 1 }} />
              {error ? 'Download Error' : 'Downloading Report'}
            </Typography>
            
            {onClose && (
              <Tooltip title="Close">
                <IconButton onClick={onClose} size="small">
                  <CloseIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
          
          <Divider sx={{ mb: 2 }} />
          
          {/* Error state */}
          {error ? (
            <Box>
              <Alert 
                severity="error"
                icon={<ErrorIcon />}
                sx={{ mb: 2 }}
              >
                {error}
              </Alert>
              
              {onRetry && (
                <Button 
                  variant="contained" 
                  color="primary" 
                  onClick={handleRetry}
                  fullWidth
                >
                  Retry Download
                </Button>
              )}
            </Box>
          ) : (
            // Download progress
            <Box>
              {/* File info */}
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ mb: 0.5 }}>
                  <strong>File:</strong> {fileName}
                </Typography>
                {fileSize > 0 && (
                  <Typography variant="body2" sx={{ mb: 0.5 }}>
                    <strong>Size:</strong> {formatBytes(fileSize)}
                  </Typography>
                )}
              </Box>
              
              {/* Progress bar */}
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2">
                    {progress < 100 ? 'Downloading...' : 'Download Complete!'}
                  </Typography>
                  <Typography variant="body2">
                    {progress.toFixed(0)}%
                  </Typography>
                </Box>
                
                <LinearProgress 
                  variant="determinate" 
                  value={progress} 
                  sx={{ 
                    height: 10, 
                    borderRadius: 5,
                    mb: 1
                  }} 
                />
                
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" color="text.secondary">
                    {formatBytes(downloadedBytes)} of {formatBytes(fileSize)} ({formatBytes(downloadSpeed)}/s)
                  </Typography>
                  
                  <Typography variant="caption" color="text.secondary">
                    {progress < 100 ? `Est. time: ${formatTimeRemaining(timeRemaining)}` : ''}
                  </Typography>
                </Box>
              </Box>
              
              {/* Completion message */}
              {progress >= 100 && (
                <Box 
                  sx={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    p: 1,
                    bgcolor: 'success.light',
                    borderRadius: 1,
                    color: 'success.contrastText'
                  }}
                >
                  <CheckCircleIcon sx={{ mr: 1 }} />
                  <Typography variant="body2" fontWeight="medium">
                    Download completed successfully!
                  </Typography>
                </Box>
              )}
              
              {/* Loading spinner for very start of download */}
              {progress === 0 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', my: 2 }}>
                  <CircularProgress size={40} thickness={4} />
                </Box>
              )}
            </Box>
          )}
        </Paper>
      </Fade>
    </Backdrop>
  );
};

export default DownloadProgressTracker; 