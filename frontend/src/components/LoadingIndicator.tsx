import React from 'react';
import {
  Box,
  CircularProgress,
  LinearProgress,
  Typography,
  Button,
  Alert,
  Paper,
  Stack
} from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';

export type LoadingStage = 'initial' | 'loading' | 'retrying' | 'error' | 'completed' | 'generating' | 'analyzing' | 'refining';

export interface LoadingState {
  isLoading: boolean;
  progress?: number;
  stage?: LoadingStage;
  message?: string;
  error?: string;
  attempt?: number;
  maxAttempts?: number;
}

export interface LoadingIndicatorProps {
  /**
   * The current loading state
   */
  state: LoadingState;
  
  /**
   * Whether to show a linear progress bar (default) or circular progress
   */
  variant?: 'linear' | 'circular' | 'indeterminate';
  
  /**
   * Handler for retry button click
   */
  onRetry?: () => void;
  
  /**
   * Additional CSS styles
   */
  sx?: any;
  
  /**
   * Whether to show the loading indicator even when not loading
   */
  alwaysShow?: boolean;
}

const stageMessages: Record<LoadingStage, string> = {
  initial: 'Preparazione...',
  loading: 'Caricamento in corso...',
  retrying: 'Riprovo la connessione...',
  error: 'Si è verificato un errore',
  completed: 'Completato',
  generating: 'Generazione del report in corso...',
  analyzing: 'Analisi dei documenti in corso...',
  refining: 'Raffinamento del report in corso...'
};

/**
 * A standardized loading indicator component that shows different states
 * including progress bars, retry options, and contextual messages
 */
const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({
  state,
  variant = 'linear',
  onRetry,
  sx = {},
  alwaysShow = false
}) => {
  const { isLoading, progress = 0, stage = 'loading', message, error, attempt, maxAttempts } = state;
  
  // If not loading and not set to always show, don't render anything
  if (!isLoading && !alwaysShow && !error) {
    return null;
  }
  
  // If there's an error, show error state
  if (error) {
    return (
      <Alert 
        severity="error"
        action={
          onRetry && (
            <Button 
              color="inherit" 
              size="small"
              startIcon={<RefreshIcon />}
              onClick={onRetry}
            >
              Riprova
            </Button>
          )
        }
        sx={{ mt: 2, mb: 2, ...sx }}
      >
        {error}
      </Alert>
    );
  }
  
  // Get the appropriate message based on stage
  const displayMessage = message || stageMessages[stage] || 'Caricamento...';
  
  // If retrying, show the attempt count
  const retryInfo = stage === 'retrying' && attempt && maxAttempts 
    ? ` (Tentativo ${attempt}/${maxAttempts})`
    : '';
  
  return (
    <Box sx={{ width: '100%', mt: 2, mb: 2, ...sx }}>
      <Stack spacing={1} alignItems="center">
        {/* Loading text */}
        <Typography variant="body2" color="text.secondary">
          {displayMessage}{retryInfo}
        </Typography>
        
        {/* Progress indicator */}
        {variant === 'circular' ? (
          <CircularProgress 
            variant={progress > 0 ? 'determinate' : 'indeterminate'} 
            value={progress} 
            size={40}
          />
        ) : (
          <LinearProgress 
            variant={progress > 0 ? 'determinate' : 'indeterminate'} 
            value={progress} 
            sx={{ width: '100%', borderRadius: 1 }}
          />
        )}
        
        {/* Retry button (if provided and in error/retry state) */}
        {onRetry && (stage === 'error' || stage === 'retrying') && (
          <Button 
            variant="outlined" 
            size="small" 
            startIcon={<RefreshIcon />}
            onClick={onRetry}
            sx={{ mt: 1 }}
          >
            Riprova
          </Button>
        )}
      </Stack>
    </Box>
  );
};

export default LoadingIndicator; 