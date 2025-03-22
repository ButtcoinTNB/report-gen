import { logger } from './logger';

/**
 * Standard error response format for API errors
 */
export interface ApiError {
  message: string;
  code: string;
  status: number;
  details?: any;
}

/**
 * Options for error handling
 */
export interface ErrorHandlerOptions {
  /** Context where the error occurred (for better logging) */
  context?: string;
  /** Whether to show the error to the user */
  showUser?: boolean;
  /** Custom handler for specific error types */
  onSpecificError?: (error: any) => boolean;
}

/**
 * Helper function to extract useful error information from various error formats
 * @param error The error object from catch block
 * @returns A clean error message string
 */
export function getErrorMessage(error: any): string {
  if (!error) return 'An unknown error occurred';
  
  // Handle string errors
  if (typeof error === 'string') return error;
  
  // Handle Error objects
  if (error instanceof Error) return error.message;
  
  // Handle Axios errors
  if (error.response) {
    const { data, status } = error.response;
    
    // Try to get message from response data
    if (data) {
      if (typeof data === 'string') return data;
      if (data.message) return data.message;
      if (data.detail) return data.detail;
      if (data.error) return typeof data.error === 'string' ? data.error : 'Server error';
    }
    
    // Fallback to status code
    return `Request failed with status code ${status}`;
  }
  
  // Network errors
  if (error.request) return 'No response received from server';
  
  // Unknown errors
  return error.message || 'An unknown error occurred';
}

/**
 * Centralized error handler for consistency across the application
 * @param error The caught error
 * @param options Error handling options
 * @returns Standardized error object
 */
export function handleError(error: any, options: ErrorHandlerOptions = {}): ApiError {
  const { context = 'application', showUser = false } = options;
  
  // Log the error (with context)
  logger.error(`Error in ${context}:`, error);
  
  // If it's an axios error, log additional details
  if (error.response) {
    logger.error('Response status:', error.response.status);
    logger.error('Response data:', error.response.data);
  }
  
  // Extract a clean error message
  const message = getErrorMessage(error);
  
  // Create a standardized error object
  const apiError: ApiError = {
    message,
    code: error.code || 'UNKNOWN_ERROR',
    status: error.response?.status || 500,
    details: error.response?.data || undefined
  };
  
  // Call the specific error handler if provided
  if (options.onSpecificError) {
    options.onSpecificError(apiError);
  }
  
  return apiError;
}

/**
 * Error categories for better error handling and user feedback
 */
export enum ErrorCategory {
  NETWORK = 'network',
  SERVER = 'server',
  FILE_TYPE = 'file_type',
  FILE_SIZE = 'file_size',
  PERMISSION = 'permission',
  QUOTA = 'quota',
  UNKNOWN = 'unknown'
}

/**
 * Interface for structured error information
 */
export interface StructuredError {
  message: string;
  category: ErrorCategory;
  technicalDetails?: string;
  userGuidance: string;
  retryable: boolean;
}

/**
 * Maps HTTP status codes to error categories
 */
const statusToCategory = (status: number): ErrorCategory => {
  if (status >= 500) return ErrorCategory.SERVER;
  if (status === 413) return ErrorCategory.FILE_SIZE;
  if (status === 415) return ErrorCategory.FILE_TYPE;
  if (status === 403) return ErrorCategory.PERMISSION;
  if (status === 429) return ErrorCategory.QUOTA;
  if (status >= 400) return ErrorCategory.SERVER;
  return ErrorCategory.UNKNOWN;
};

/**
 * Maps error categories to user-friendly guidance
 */
const categoryToGuidance = (category: ErrorCategory): string => {
  switch (category) {
    case ErrorCategory.NETWORK:
      return 'Verifica la tua connessione internet e riprova. Se il problema persiste, prova a ricaricare la pagina.';
    case ErrorCategory.SERVER:
      return 'Si è verificato un errore sul server. Riprova più tardi o contatta il supporto se il problema persiste.';
    case ErrorCategory.FILE_TYPE:
      return 'Il formato del file non è supportato. Utilizza solo file nei formati PDF, DOCX, DOC o TXT.';
    case ErrorCategory.FILE_SIZE:
      return 'Il file è troppo grande. La dimensione massima consentita è 100 MB. Prova a comprimere il file o suddividerlo in file più piccoli.';
    case ErrorCategory.PERMISSION:
      return 'Non hai i permessi necessari per caricare questo file. Verifica di aver effettuato l\'accesso o contatta l\'amministratore.';
    case ErrorCategory.QUOTA:
      return 'Hai raggiunto il limite di caricamenti. Riprova più tardi o contatta l\'amministratore per aumentare la quota.';
    case ErrorCategory.UNKNOWN:
    default:
      return 'Si è verificato un errore imprevisto. Riprova o contatta il supporto se il problema persiste.';
  }
};

/**
 * Determines if an error is retryable based on its category
 */
const isRetryable = (category: ErrorCategory): boolean => {
  return [
    ErrorCategory.NETWORK,
    ErrorCategory.SERVER,
    ErrorCategory.UNKNOWN,
    ErrorCategory.QUOTA
  ].includes(category);
};

/**
 * Processes an error into a structured format with user guidance
 */
export const processUploadError = (error: any): StructuredError => {
  logger.error('Processing upload error:', error);
  
  // Default to unknown category
  let category = ErrorCategory.UNKNOWN;
  let message = 'Errore sconosciuto durante il caricamento';
  let technicalDetails = '';
  
  // Handle different error types
  if (error instanceof Error) {
    message = error.message;
    
    // Check for network errors
    if (
      error.name === 'NetworkError' || 
      error.message.includes('network') ||
      error.message.includes('connection') ||
      error.message.includes('offline')
    ) {
      category = ErrorCategory.NETWORK;
    }
  }
  
  // Handle response errors with status codes
  if (error && error.status) {
    category = statusToCategory(error.status);
    technicalDetails = `Status: ${error.status}`;
    
    // Extract more details from response if available
    if (error.data && error.data.message) {
      message = error.data.message;
    }
  }
  
  // Check for file type errors
  if (
    message.toLowerCase().includes('file type') || 
    message.toLowerCase().includes('format') || 
    message.toLowerCase().includes('mime')
  ) {
    category = ErrorCategory.FILE_TYPE;
  }
  
  // Check for file size errors
  if (
    message.toLowerCase().includes('size') || 
    message.toLowerCase().includes('too large') || 
    message.toLowerCase().includes('troppo grande')
  ) {
    category = ErrorCategory.FILE_SIZE;
  }
  
  // Get user guidance based on category
  const userGuidance = categoryToGuidance(category);
  
  // Determine if the error is retryable
  const retryable = isRetryable(category);
  
  return {
    message,
    category,
    technicalDetails,
    userGuidance,
    retryable
  };
};

/**
 * Formats a structured error into a user-friendly message
 */
export const formatErrorForUser = (error: StructuredError): string => {
  return `${error.message}. ${error.userGuidance}`;
};

export default {
  processUploadError,
  formatErrorForUser,
  ErrorCategory,
  isRetryable: (category: ErrorCategory) => isRetryable(category)
}; 