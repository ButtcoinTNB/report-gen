import React, { useState, useCallback, ComponentType } from 'react';
import { Snackbar, Alert } from '@mui/material';
import { useErrorHandler } from '../hooks/useErrorHandler';

/**
 * A Higher Order Component that adds standardized error handling to any component
 */
export function withErrorHandling<P extends object>(
  Component: ComponentType<P & WithErrorHandlingProps>
): ComponentType<P> {
  return (props: P) => {
    const [error, setError] = useState<string | null>(null);
    const { handleError } = useErrorHandler({
      showNotification: false, // We'll handle notifications ourselves
    });

    // Function to handle errors that will be passed to the wrapped component
    const handleComponentError = useCallback((err: unknown, options: { showNotification?: boolean } = {}) => {
      const normalizedError = err instanceof Error ? err : new Error(String(err));
      handleError(normalizedError, { 
        showNotification: false, // Don't show notification via the global handler
        logError: true 
      });
      
      // Set error for our local notification
      if (options.showNotification !== false) {
        setError(normalizedError.message);
      }
      
      return normalizedError;
    }, [handleError]);

    // Clear error state
    const clearError = useCallback(() => {
      setError(null);
    }, []);

    return (
      <>
        <Component
          {...props as P}
          handleError={handleComponentError}
          clearError={clearError}
          error={error}
        />
        
        {/* Standardized error notification */}
        <Snackbar
          open={!!error}
          autoHideDuration={6000}
          onClose={clearError}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert onClose={clearError} severity="error" variant="filled">
            {error}
          </Alert>
        </Snackbar>
      </>
    );
  };
}

// Props that will be injected by the HOC
export interface WithErrorHandlingProps {
  handleError: (error: unknown, options?: { showNotification?: boolean }) => Error;
  clearError: () => void;
  error: string | null;
} 