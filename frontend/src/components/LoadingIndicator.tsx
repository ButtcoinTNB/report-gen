import React from 'react';
import {
  Box,
  CircularProgress,
  LinearProgress,
  Typography,
  Button,
  Alert,
  Paper,
  Stack,
  SxProps,
  Theme
} from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';

export type LoadingStage = 'initial' | 'loading' | 'uploading' | 'retrying' | 'error' | 'completed' | 'generating' | 'analyzing' | 'refining';

/**
 * Interface for the loading state used throughout the application
 */
export interface LoadingState {
  /** Whether the component is currently in a loading state */
  isLoading: boolean;
  /** Optional progress value (0-100) */
  progress?: number;
  /** The current loading stage */
  stage?: LoadingStage;
  /** Optional message to display */
  message?: string;
  /** Optional error message if there was an error */
  error?: string | null;
  /** Current attempt number (for retries) */
  attempt?: number;
  /** Maximum number of attempts allowed */
  maxAttempts?: number;
}

/**
 * Props for the LoadingIndicator component
 */
export interface LoadingIndicatorProps {
  /**
   * The current loading state
   */
  loadingState: LoadingState;
  
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
  sx?: SxProps<Theme>;
  
  /**
   * Whether to show the loading indicator even when not loading
   */
  alwaysShow?: boolean;
}

// Define messages for each stage
const stageMessages: Record<LoadingStage, string> = {
  initial: 'Inizializzazione...',
  loading: 'Caricamento in corso...',
  uploading: 'Caricamento dei file...',
  retrying: 'Nuovo tentativo...',
  error: 'Si è verificato un errore',
  completed: 'Completato!',
  generating: 'Generazione report in corso...',
  analyzing: 'Analisi documenti in corso...',
  refining: 'Affinamento report in corso...'
};

/**
 * A standardized loading indicator component that shows different states
 * including progress bars, retry options, and contextual messages
 */
const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({
  loadingState,
  variant = 'linear',
  onRetry,
  sx = {},
  alwaysShow = false
}) => {
  const { isLoading, progress = 0, stage = 'loading', message, error, attempt, maxAttempts } = loadingState;
  
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