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

export default {
  handleError,
  getErrorMessage,
  logger
}; 