import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  LinearProgress, 
  Stack, 
  Chip,
  Alert,
  Button,
  Collapse,
  CircularProgress,
  Grid,
  IconButton,
  Tooltip,
  AlertTitle
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CloudDoneIcon from '@mui/icons-material/CloudDone';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import ReplayIcon from '@mui/icons-material/Replay';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import StorageIcon from '@mui/icons-material/Storage';
import LockIcon from '@mui/icons-material/Lock';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import { useAppSelector } from '../store/hooks';
import { ErrorCategory } from '../utils/errorHandler';

export type UploadProgressVariant = 'compact' | 'full';

export interface UploadProgressTrackerProps {
  onRetry?: () => void;
  showDetails?: boolean;
  variant?: UploadProgressVariant;
}

/**
 * Gets the appropriate icon for an error category
 */
const getErrorIcon = (errorCategory?: string) => {
  switch (errorCategory) {
    case ErrorCategory.NETWORK:
      return <WifiOffIcon />;
    case ErrorCategory.FILE_TYPE:
      return <AttachFileIcon />;
    case ErrorCategory.FILE_SIZE:
      return <StorageIcon />;
    case ErrorCategory.PERMISSION:
      return <LockIcon />;
    case ErrorCategory.QUOTA:
      return <HourglassEmptyIcon />;
    case ErrorCategory.SERVER:
    case ErrorCategory.UNKNOWN:
    default:
      return <ErrorOutlineIcon />;
  }
};

/**
 * Component that displays the progress of background file uploads
 * Shows overall progress, individual file status, and error messages
 */
const UploadProgressTracker: React.FC<UploadProgressTrackerProps> = ({
  onRetry,
  showDetails = false,
  variant = 'full'
}) => {
  const { backgroundUpload } = useAppSelector(state => state.report);
  const [expanded, setExpanded] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  
  // For time tracking since upload started
  useEffect(() => {
    if (!backgroundUpload?.isUploading) return;
    
    const startTime = backgroundUpload.uploadStartTime || Date.now();
    const interval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    
    return () => clearInterval(interval);
  }, [backgroundUpload?.isUploading, backgroundUpload?.uploadStartTime]);
  
  // Only render if there's upload activity or showDetails is true
  const shouldRender = showDetails || 
                      (backgroundUpload && 
                       (backgroundUpload.isUploading || 
                        backgroundUpload.error || 
                        backgroundUpload.progress > 0));
  
  if (!shouldRender) return null;
  
  // Format elapsed time as mm:ss
  const formatElapsedTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };
  
  // Handle expand/collapse of details
  const toggleExpanded = () => {
    setExpanded(!expanded);
  };

  // Extract error details if available
  const errorDetails = backgroundUpload?.errorDetails || {};
  const errorCategory = errorDetails.category || ErrorCategory.UNKNOWN;
  const errorGuidance = errorDetails.userGuidance || '';
  const isRetryable = errorDetails.retryable !== undefined ? errorDetails.retryable : true;
  
  // If variant is compact, show a minimal version
  if (variant === 'compact') {
    return (
      <Box sx={{ width: '100%', mt: 1, mb: 1 }}>
        {backgroundUpload?.isUploading ? (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <CircularProgress 
              size={16} 
              sx={{ mr: 1 }} 
              variant={backgroundUpload.progress > 0 ? 'determinate' : 'indeterminate'}
              value={backgroundUpload.progress}
            />
            <Typography variant="caption" color="text.secondary">
              Caricamento {backgroundUpload.uploadedFiles}/{backgroundUpload.totalFiles} file...
            </Typography>
          </Box>
        ) : backgroundUpload?.error ? (
          <Alert 
            severity="error" 
            sx={{ py: 0 }}
            icon={getErrorIcon(errorCategory)}
          >
            {backgroundUpload.error}
          </Alert>
        ) : backgroundUpload?.progress === 100 ? (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <CloudDoneIcon color="success" sx={{ mr: 1, fontSize: 16 }} />
            <Typography variant="caption" color="success.main">
              {backgroundUpload.uploadedFiles} file caricati con successo
            </Typography>
          </Box>
        ) : null}
      </Box>
    );
  }
  
  // Full variant with detailed progress and expandable file list
  return (
    <Paper 
      elevation={1} 
      sx={{ 
        p: 2, 
        my: 2,
        borderRadius: 2,
        bgcolor: backgroundUpload?.error ? 'error.lighter' : 'background.paper',
        transition: 'background-color 0.3s ease'
      }}
    >
      <Stack spacing={2}>
        {/* Header with overall progress */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {backgroundUpload?.isUploading ? (
              <CloudUploadIcon color="primary" sx={{ mr: 1 }} />
            ) : backgroundUpload?.error ? (
              getErrorIcon(errorCategory)
            ) : (
              <CloudDoneIcon color="success" sx={{ mr: 1 }} />
            )}
            
            <Typography variant="body1" fontWeight="medium">
              {backgroundUpload?.isUploading ? 'Caricamento in corso...' : 
               backgroundUpload?.error ? 'Errore di caricamento' : 
               'Caricamento completato'}
            </Typography>
          </Box>
          
          {/* Time elapsed for active uploads */}
          {backgroundUpload?.isUploading && (
            <Typography variant="caption" color="text.secondary">
              {formatElapsedTime(elapsedTime)}
            </Typography>
          )}
        </Box>
        
        {/* Progress bar */}
        {(backgroundUpload?.isUploading || backgroundUpload?.progress > 0) && (
          <Box sx={{ width: '100%' }}>
            <LinearProgress 
              variant={backgroundUpload?.progress > 0 ? 'determinate' : 'indeterminate'} 
              value={backgroundUpload?.progress} 
              sx={{ height: 8, borderRadius: 4 }}
            />
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
              <Typography variant="caption" color="text.secondary">
                {backgroundUpload?.uploadedFiles}/{backgroundUpload?.totalFiles} file
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {backgroundUpload?.progress}%
              </Typography>
            </Box>
          </Box>
        )}
        
        {/* Enhanced error message with guidance */}
        {backgroundUpload?.error && (
          <Alert 
            severity="error"
            icon={getErrorIcon(errorCategory)}
            action={
              onRetry && isRetryable && (
                <Button 
                  color="inherit" 
                  size="small"
                  startIcon={<ReplayIcon />}
                  onClick={onRetry}
                >
                  Riprova
                </Button>
              )
            }
          >
            <AlertTitle>{backgroundUpload.error}</AlertTitle>
            {errorGuidance}
          </Alert>
        )}
        
        {/* File status summary */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Grid container spacing={1}>
            <Grid item>
              <Chip 
                label={`${backgroundUpload?.uploadedFiles || 0} completati`} 
                color="success" 
                size="small" 
                icon={<CloudDoneIcon />}
              />
            </Grid>
            {backgroundUpload?.isUploading && backgroundUpload.uploadedFiles < backgroundUpload.totalFiles && (
              <Grid item>
                <Chip 
                  label={`${backgroundUpload.totalFiles - backgroundUpload.uploadedFiles} in corso`} 
                  color="primary" 
                  size="small" 
                  icon={<CloudUploadIcon />}
                />
              </Grid>
            )}
          </Grid>
          
          {/* Expand/collapse toggle */}
          <Tooltip title={expanded ? "Nascondi dettagli" : "Mostra dettagli"}>
            <IconButton size="small" onClick={toggleExpanded}>
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Tooltip>
        </Box>
        
        {/* Expanded details section with additional error info if available */}
        <Collapse in={expanded}>
          <Paper variant="outlined" sx={{ p: 1, mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              ID Sessione: {backgroundUpload?.uploadSessionId || 'N/A'}
            </Typography>
            
            {backgroundUpload?.error && errorDetails.technicalDetails && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                  Dettagli tecnici: {errorDetails.technicalDetails}
                </Typography>
              </Box>
            )}
          </Paper>
        </Collapse>
      </Stack>
    </Paper>
  );
};

export default UploadProgressTracker; 