import { useCallback } from 'react';
import { useSnackbar } from 'notistack';
import { APIError, NetworkError, TimeoutError } from '../services/api';

export interface ErrorHandlerOptions {
  /**
   * If true, error will be logged to console
   */
  logToConsole?: boolean;
  
  /**
   * If true, error will be shown to user via snackbar
   */
  showToUser?: boolean;
  
  /**
   * Custom error messages by error type
   */
  customMessages?: {
    api?: string;
    network?: string;
    timeout?: string;
    unknown?: string;
  };
  
  /**
   * Callback to execute after error is handled
   */
  onError?: (error: Error) => void;
}

/**
 * Hook that provides standardized error handling throughout the application
 */
export const useErrorHandler = () => {
  const { enqueueSnackbar } = useSnackbar();
  
  /**
   * Handles errors in a consistent way across the application
   */
  const handleError = useCallback((error: unknown, options?: ErrorHandlerOptions) => {
    const {
      logToConsole = true,
      showToUser = true,
      customMessages = {},
      onError
    } = options || {};
    
    // Default error messages in Italian
    const defaultMessages = {
      api: 'Si è verificato un errore durante la comunicazione con il server.',
      network: 'Impossibile connettersi al server. Verifica la tua connessione internet.',
      timeout: 'La richiesta ha impiegato troppo tempo. Riprova più tardi.',
      unknown: 'Si è verificato un errore imprevisto. Riprova o contatta l\'assistenza.'
    };
    
    // Merge default with custom messages
    const messages = { ...defaultMessages, ...customMessages };
    
    // Determine error type and message
    let errorMessage = messages.unknown;
    let errorType = 'error';
    
    if (error instanceof APIError) {
      errorMessage = messages.api;
      // Include status code and server message if available
      if (error.status && error.message) {
        errorMessage = `${errorMessage} (${error.status}: ${error.message})`;
      }
    } else if (error instanceof NetworkError) {
      errorMessage = messages.network;
      errorType = 'warning';
    } else if (error instanceof TimeoutError) {
      errorMessage = messages.timeout;
      errorType = 'warning';
    }
    
    // Log to console if enabled
    if (logToConsole) {
      console.error('Error caught by useErrorHandler:', error);
    }
    
    // Show to user if enabled
    if (showToUser) {
      enqueueSnackbar(errorMessage, { 
        variant: errorType as any,
        autoHideDuration: 5000,
        preventDuplicate: true
      });
    }
    
    // Execute callback if provided
    if (onError) {
      onError(error instanceof Error ? error : new Error(String(error)));
    }
    
    return error;
  }, [enqueueSnackbar]);
  
  /**
   * Wraps a promise with error handling
   */
  const wrapPromise = useCallback(<T>(
    promise: Promise<T>, 
    options?: ErrorHandlerOptions
  ): Promise<T> => {
    return promise.catch(error => {
      handleError(error, options);
      throw error; // Re-throw to allow further handling
    });
  }, [handleError]);
  
  return { 
    handleError,
    wrapPromise
  };
};

export default useErrorHandler; 