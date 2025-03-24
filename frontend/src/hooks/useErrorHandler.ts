import { useCallback } from 'react';
import { useSnackbar } from 'notistack';
import { APIError, NetworkError, TimeoutError } from '../services/api';

interface ErrorHandlerOptions {
  showNotification?: boolean;
  logError?: boolean;
  onError?: (error: Error) => void;
}

export const useErrorHandler = (defaultOptions: ErrorHandlerOptions = {}) => {
  const { enqueueSnackbar } = useSnackbar();

  const handleError = useCallback(
    (error: unknown, options: ErrorHandlerOptions = {}) => {
      const {
        showNotification = true,
        logError = true,
        onError,
      } = { ...defaultOptions, ...options };

      // Ensure we have an Error object
      const normalizedError = error instanceof Error ? error : new Error(String(error));

      // Log error if enabled
      if (logError) {
        console.error('Error caught by handler:', normalizedError);
      }

      // Handle different error types
      if (normalizedError instanceof APIError) {
        if (showNotification) {
          let message = normalizedError.message;
          
          // Add more context for specific error codes
          switch (normalizedError.code) {
            case 'VALIDATION_ERROR':
              message = 'I dati inseriti non sono validi. Controlla e riprova.';
              break;
            case 'UNAUTHORIZED':
              message = 'Sessione scaduta. Effettua nuovamente il login.';
              break;
            case 'FORBIDDEN':
              message = 'Non hai i permessi necessari per questa operazione.';
              break;
            case 'NOT_FOUND':
              message = 'La risorsa richiesta non è stata trovata.';
              break;
            case 'RATE_LIMIT_EXCEEDED':
              message = 'Troppe richieste. Riprova tra qualche minuto.';
              break;
          }

          enqueueSnackbar(message, {
            variant: 'error',
            autoHideDuration: 5000,
          });
        }
      } else if (normalizedError instanceof NetworkError) {
        if (showNotification) {
          enqueueSnackbar(
            'Errore di connessione. Verifica la tua connessione e riprova.',
            {
              variant: 'error',
              autoHideDuration: 5000,
            }
          );
        }
      } else if (normalizedError instanceof TimeoutError) {
        if (showNotification) {
          enqueueSnackbar(
            'La richiesta sta impiegando troppo tempo. Riprova più tardi.',
            {
              variant: 'error',
              autoHideDuration: 5000,
            }
          );
        }
      } else {
        // Generic error
        if (showNotification) {
          enqueueSnackbar(
            'Si è verificato un errore imprevisto. Riprova più tardi.',
            {
              variant: 'error',
              autoHideDuration: 5000,
            }
          );
        }
      }

      // Call custom error handler if provided
      if (onError) {
        onError(normalizedError);
      }

      return normalizedError;
    },
    [enqueueSnackbar]
  );

  const wrapPromise = useCallback(
    async <T>(
      promise: Promise<T>,
      options: ErrorHandlerOptions = {}
    ): Promise<T> => {
      try {
        return await promise;
      } catch (error) {
        handleError(error, options);
        throw error;
      }
    },
    [handleError]
  );

  return {
    handleError,
    wrapPromise,
  };
}; 