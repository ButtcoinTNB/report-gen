/**
 * Error handling utilities for API requests and responses
 */
import axios, { AxiosError } from 'axios';

// Interface for standard error format
export interface ApiError {
  status: 'error';
  message: string;
  code?: string;
  details?: any;
}

// Standard error responses
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection and try again.',
  SERVER_ERROR: 'Server error. Please try again later.',
  TIMEOUT_ERROR: 'Request timed out. Please try again.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  NOT_FOUND: 'The requested resource was not found.',
  BAD_REQUEST: 'Invalid request. Please check your input and try again.',
  UNKNOWN_ERROR: 'An unknown error occurred. Please try again.',
};

/**
 * Transform any error into a standardized API error format
 * This ensures consistent error handling throughout the application
 * 
 * @param {Error|AxiosError|any} error - The error to transform
 * @param {Object} options - Additional options
 * @param {boolean} options.includeDetails - Whether to include error details in the response
 * @returns {ApiError} Standardized error object
 */
export function normalizeError(
  error: Error | AxiosError | any, 
  { includeDetails = false }: { includeDetails?: boolean } = {}
): ApiError {
  // Already in the right format
  if (error && error.status === 'error' && error.message) {
    return error as ApiError;
  }
  
  // For Axios errors
  if (axios.isAxiosError(error)) {
    // Handle network errors
    if (error.code === 'ERR_NETWORK') {
      return {
        status: 'error',
        message: ERROR_MESSAGES.NETWORK_ERROR,
        code: 'NETWORK_ERROR',
        ...(includeDetails ? { details: error.message } : {})
      };
    }
    
    // Handle timeout errors
    if (error.code === 'ECONNABORTED') {
      return {
        status: 'error',
        message: ERROR_MESSAGES.TIMEOUT_ERROR,
        code: 'TIMEOUT_ERROR',
        ...(includeDetails ? { details: error.message } : {})
      };
    }
    
    // If there's a response from the server
    if (error.response) {
      const { status, data } = error.response;
      
      // Server already returned error in the expected format
      if (data && data.status === 'error' && data.message) {
        return data as ApiError;
      }
      
      // Transform based on status code
      switch (status) {
        case 400:
          return {
            status: 'error',
            message: data?.message || ERROR_MESSAGES.BAD_REQUEST,
            code: 'BAD_REQUEST',
            ...(includeDetails ? { details: data } : {})
          };
        case 401:
        case 403:
          return {
            status: 'error',
            message: data?.message || ERROR_MESSAGES.UNAUTHORIZED,
            code: 'UNAUTHORIZED',
            ...(includeDetails ? { details: data } : {})
          };
        case 404:
          return {
            status: 'error',
            message: data?.message || ERROR_MESSAGES.NOT_FOUND,
            code: 'NOT_FOUND',
            ...(includeDetails ? { details: data } : {})
          };
        case 500:
        case 502:
        case 503:
        case 504:
          return {
            status: 'error',
            message: data?.message || ERROR_MESSAGES.SERVER_ERROR,
            code: 'SERVER_ERROR',
            ...(includeDetails ? { details: data } : {})
          };
        default:
          return {
            status: 'error',
            message: data?.message || ERROR_MESSAGES.UNKNOWN_ERROR,
            code: `HTTP_ERROR_${status}`,
            ...(includeDetails ? { details: data } : {})
          };
      }
    }
  }
  
  // For regular Error objects or other error types
  return {
    status: 'error',
    message: error?.message || ERROR_MESSAGES.UNKNOWN_ERROR,
    code: 'UNKNOWN_ERROR',
    ...(includeDetails ? { details: error } : {})
  };
}

/**
 * Handle errors from API requests and convert to normalized format
 * 
 * @param {Error|AxiosError|any} error - The error to handle
 * @param {boolean} throwError - Whether to throw the normalized error
 * @returns {ApiError} Normalized error object
 */
export function handleApiError(
  error: Error | AxiosError | any, 
  throwError: boolean = false
): ApiError {
  const normalizedError = normalizeError(error);
  
  // Log the error in development
  if (process.env.NODE_ENV !== 'production') {
    console.error('API Error:', normalizedError, error);
  }
  
  if (throwError) {
    throw normalizedError;
  }
  
  return normalizedError;
} 