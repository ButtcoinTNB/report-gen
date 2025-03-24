/**
 * Centralized error handling for the frontend application
 * Provides standardized error handling, reporting, and display.
 */

import { AxiosError } from 'axios';
import { logger } from './logger';
import { toast } from 'react-toastify';
import React from 'react';

// Error severity levels
export enum ErrorSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical'
}

// Error categories
export enum ErrorCategory {
  NETWORK = 'network',
  API = 'api',
  VALIDATION = 'validation',
  AUTH = 'auth',
  TIMEOUT = 'timeout',
  INTERNAL = 'internal',
  UNKNOWN = 'unknown'
}

// Error codes used throughout the application
export enum ErrorCode {
  // Authentication errors
  UNAUTHORIZED = 'unauthorized',
  FORBIDDEN = 'forbidden',
  
  // Validation errors
  VALIDATION = 'validation',
  INVALID_INPUT = 'invalid_input',
  INVALID_FILE = 'invalid_file',
  
  // Resource errors
  NOT_FOUND = 'not_found',
  ALREADY_EXISTS = 'already_exists',
  
  // System errors
  INTERNAL = 'internal',
  SERVICE_UNAVAILABLE = 'service_unavailable',
  NETWORK = 'network',
  TIMEOUT = 'timeout',
  
  // Rate limiting
  RATE_LIMITED = 'rate_limited',
  
  // Default
  UNKNOWN = 'unknown'
}

// Standard error interface
export interface AppError {
  message: string;
  severity: ErrorSeverity;
  category: ErrorCategory;
  originalError?: any;
  code?: string;
  context?: Record<string, any>;
  timestamp: number;
  transactionId?: string;
  retryable: boolean;
  userGuidance?: string;
}

// Context collection function type
export type ContextCollector = () => Record<string, any>;

// Global context collectors
const contextCollectors: ContextCollector[] = [];

/**
 * Create a standardized error object from any error
 * 
 * @param originalError - The original error
 * @param options - Options for creating the error
 * @returns Standardized AppError
 */
export function createError(
  originalError: any,
  options: {
    message?: string;
    severity?: ErrorSeverity;
    category?: ErrorCategory;
    code?: string;
    context?: Record<string, any>;
    transactionId?: string;
    retryable?: boolean;
    userGuidance?: string;
  } = {}
): AppError {
  // Default error values
  const defaultErrorValues: Partial<AppError> = {
    message: 'An unexpected error occurred',
    severity: ErrorSeverity.ERROR,
    category: ErrorCategory.UNKNOWN,
    timestamp: Date.now(),
    retryable: false
  };

  // Extract error info from different error types
  let extractedInfo: Partial<AppError> = {};

  if (originalError) {
    if (originalError instanceof Error) {
      extractedInfo.message = originalError.message;
    }

    // Handle Axios errors
    if (originalError.isAxiosError) {
      const axiosError = originalError as AxiosError;
      
      // Set category based on axios error
      if (axiosError.code === 'ECONNABORTED') {
        extractedInfo.category = ErrorCategory.TIMEOUT;
        extractedInfo.retryable = true;
      } else if (!axiosError.response) {
        extractedInfo.category = ErrorCategory.NETWORK;
        extractedInfo.retryable = true;
      } else {
        extractedInfo.category = ErrorCategory.API;
        
        // Extract API error details if available
        const data = axiosError.response?.data as any;
        if (data) {
          if (data.message) extractedInfo.message = data.message;
          if (data.code) extractedInfo.code = data.code;
          if (data.transactionId) extractedInfo.transactionId = data.transactionId;
        }
        
        // Set retryable based on status code
        const status = axiosError.response?.status;
        extractedInfo.retryable = status != null && status >= 500;
      }
    }
  }

  // Collect global context
  const globalContext = collectGlobalContext();

  // Create the final error by merging defaults, extracted info, and provided options
  const error: AppError = {
    ...defaultErrorValues,
    ...extractedInfo,
    ...options,
    context: {
      ...globalContext,
      ...extractedInfo.context,
      ...options.context
    },
    originalError
  };

  return error;
}

/**
 * Register a context collector function that will be called when creating errors
 * 
 * @param collector - Function that returns context data
 */
export function registerContextCollector(collector: ContextCollector): void {
  contextCollectors.push(collector);
}

/**
 * Collect context from all registered context collectors
 * 
 * @returns Combined context from all collectors
 */
function collectGlobalContext(): Record<string, any> {
  let context: Record<string, any> = {};
  
  for (const collector of contextCollectors) {
    try {
      const collectedContext = collector();
      context = { ...context, ...collectedContext };
    } catch (error) {
      logger.warn('Error in context collector', error);
    }
  }
  
  return context;
}

/**
 * Handle an error by logging it and optionally performing additional actions
 * 
 * @param error - The error to handle
 * @param additionalContext - Additional context to add to the error
 * @returns The handled AppError
 */
export function handleError(
  error: any,
  additionalContext: Record<string, any> = {}
): AppError {
  const appError = error instanceof Object && 'severity' in error ? 
    error as AppError : 
    createError(error);
  
  // Add additional context
  appError.context = {
    ...appError.context,
    ...additionalContext
  };
  
  // Log the error
  logError(appError);

  return appError;
}

/**
 * Log an error to the console and any configured error reporting service
 * 
 * @param error - The error to log
 */
function logError(error: AppError): void {
  const { severity, category, message, code, context } = error;
  
  // Log to console based on severity
  const logObject = {
    category,
    code,
    timestamp: new Date(error.timestamp).toISOString(),
    transactionId: error.transactionId,
    context
  };
  
  switch (severity) {
    case ErrorSeverity.INFO:
      logger.info(`[${category}] ${message}`, logObject);
      break;
    case ErrorSeverity.WARNING:
      logger.warn(`[${category}] ${message}`, logObject);
      break;
    case ErrorSeverity.ERROR:
    case ErrorSeverity.CRITICAL:
      logger.error(`[${category}] ${message}`, logObject);
      
      // For critical errors, add a console trace for easier debugging
      if (severity === ErrorSeverity.CRITICAL) {
        console.trace('Critical error occurred');
      }
      break;
  }
  
  // TODO: Add integration with error reporting service like Sentry
  // if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
  //   // Report to Sentry or other error tracking service
  // }
}

/**
 * Get a user-friendly error message based on the error
 * 
 * @param error - The error to get a message for
 * @returns User-friendly error message
 */
export function getUserFriendlyMessage(error: AppError): string {
  // Use specific user guidance if provided
  if (error.userGuidance) {
    return error.userGuidance;
  }
  
  // Default messages based on category
  switch (error.category) {
    case ErrorCategory.NETWORK:
      return 'Unable to connect to the server. Please check your internet connection and try again.';
    case ErrorCategory.TIMEOUT:
      return 'The server took too long to respond. Please try again later.';
    case ErrorCategory.AUTH:
      return 'You need to log in again to continue.';
    case ErrorCategory.VALIDATION:
      return 'Please check your input and try again.';
    case ErrorCategory.API:
      return error.message || 'There was a problem with the server. Please try again later.';
    default:
      return 'An unexpected error occurred. Please try again later.';
  }
}

/**
 * Determine if an error should allow automatic retry
 * 
 * @param error - The error to check
 * @returns True if the error is retryable
 */
export function isRetryableError(error: AppError): boolean {
  return error.retryable;
}

/**
 * Create a network error
 * 
 * @param message - Error message
 * @param originalError - Original error if available
 * @returns Network error
 */
export function createNetworkError(message: string, originalError?: any): AppError {
  return createError(originalError, {
    message,
    category: ErrorCategory.NETWORK,
    severity: ErrorSeverity.ERROR,
    retryable: true,
    userGuidance: 'Unable to connect to the server. Please check your internet connection and try again.'
  });
}

/**
 * Create a timeout error
 * 
 * @param message - Error message
 * @param originalError - Original error if available
 * @returns Timeout error
 */
export function createTimeoutError(message: string, originalError?: any): AppError {
  return createError(originalError, {
    message,
    category: ErrorCategory.TIMEOUT,
    severity: ErrorSeverity.ERROR,
    retryable: true,
    userGuidance: 'The server took too long to respond. Please try again later.'
  });
}

// Register window error handler
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    handleError(event.error, {
      errorType: 'window.onerror',
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno
    });
  });
  
  window.addEventListener('unhandledrejection', (event) => {
    handleError(event.reason, {
      errorType: 'unhandledRejection',
    });
  });
}

/**
 * Standard error structure used throughout the application
 */
export interface ApiError {
  code: string;
  message: string;
  detail?: string;
  field?: string;
  timestamp?: string;
  requestId?: string;
  path?: string;
}

/**
 * Custom error class for application errors
 */
export class AppError extends Error {
  code: string;
  detail?: string;
  field?: string;
  timestamp?: string;
  requestId?: string;
  path?: string;
  status?: number;
  
  constructor(
    message: string,
    code: string = ErrorCode.UNKNOWN,
    detail?: string,
    field?: string,
    status?: number
  ) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.detail = detail;
    this.field = field;
    this.status = status;
    this.timestamp = new Date().toISOString();
    
    // Ensure instanceof works correctly
    Object.setPrototypeOf(this, AppError.prototype);
  }
  
  /**
   * Create an AppError from an API error response
   */
  static fromApiError(apiError: ApiError, status?: number): AppError {
    const error = new AppError(
      apiError.message,
      apiError.code,
      apiError.detail,
      apiError.field,
      status
    );
    
    error.timestamp = apiError.timestamp;
    error.requestId = apiError.requestId;
    error.path = apiError.path;
    
    return error;
  }
  
  /**
   * Get a user-friendly message for this error
   */
  getUserMessage(): string {
    return this.detail || this.message;
  }
  
  /**
   * Check if this error is a specific type
   */
  is(code: string): boolean {
    return this.code === code;
  }
  
  /**
   * Check if this error should be retried
   */
  isRetryable(): boolean {
    return [
      ErrorCode.NETWORK,
      ErrorCode.TIMEOUT,
      ErrorCode.SERVICE_UNAVAILABLE,
      ErrorCode.RATE_LIMITED
    ].includes(this.code as ErrorCode);
  }
}

/**
 * Handle an API error and return a standardized AppError
 */
export function handleApiError(error: unknown): AppError {
  if (error instanceof AppError) {
    return error;
  }
  
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<any>;
    const status = axiosError.response?.status;
    
    // Network errors
    if (!axiosError.response) {
      return new AppError(
        'Network error',
        ErrorCode.NETWORK,
        axiosError.message,
        undefined,
        0
      );
    }
    
    // Timeout errors
    if (axiosError.code === 'ECONNABORTED') {
      return new AppError(
        'Request timeout',
        ErrorCode.TIMEOUT,
        'The request took too long to complete',
        undefined,
        status
      );
    }
    
    // Standard API errors
    const data = axiosError.response.data;
    if (data && typeof data === 'object' && 'code' in data) {
      return AppError.fromApiError(data as ApiError, status);
    }
    
    // HTTP status-based errors
    switch (status) {
      case 400:
        return new AppError(
          'Bad request',
          ErrorCode.VALIDATION,
          'The request was invalid',
          undefined,
          status
        );
      case 401:
        return new AppError(
          'Unauthorized',
          ErrorCode.UNAUTHORIZED,
          'You need to be logged in to access this resource',
          undefined,
          status
        );
      case 403:
        return new AppError(
          'Forbidden',
          ErrorCode.FORBIDDEN,
          'You do not have permission to access this resource',
          undefined,
          status
        );
      case 404:
        return new AppError(
          'Not found',
          ErrorCode.NOT_FOUND,
          'The requested resource was not found',
          undefined,
          status
        );
      case 409:
        return new AppError(
          'Conflict',
          ErrorCode.ALREADY_EXISTS,
          'The resource already exists',
          undefined,
          status
        );
      case 429:
        return new AppError(
          'Too many requests',
          ErrorCode.RATE_LIMITED,
          'You have made too many requests. Please try again later',
          undefined,
          status
        );
      case 500:
      case 502:
      case 503:
      case 504:
        return new AppError(
          'Server error',
          ErrorCode.SERVICE_UNAVAILABLE,
          'The server encountered an error. Please try again later',
          undefined,
          status
        );
      default:
        return new AppError(
          'Unknown error',
          ErrorCode.UNKNOWN,
          `An unexpected error occurred (${status})`,
          undefined,
          status
        );
    }
  }
  
  // Generic error handling
  return new AppError(
    'Application error',
    ErrorCode.UNKNOWN,
    error instanceof Error ? error.message : String(error)
  );
}

/**
 * Show an error toast notification
 */
export function showErrorToast(error: unknown, title?: string): void {
  const appError = error instanceof AppError 
    ? error 
    : handleApiError(error);
  
  toast.error(
    React.createElement('div', {}, [
      React.createElement('div', { className: 'font-bold', key: 'title' }, title || 'Error'),
      React.createElement('div', { key: 'message' }, appError.getUserMessage())
    ]),
    {
      position: toast.POSITION.TOP_RIGHT,
      autoClose: 5000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
    }
  );
  
  // Log the error for debugging
  console.error('[App Error]', appError);
}

/**
 * Utility to wrap a promise and handle errors
 */
export async function withErrorHandling<T>(
  promise: Promise<T>,
  errorHandler?: (error: AppError) => void
): Promise<T | null> {
  try {
    return await promise;
  } catch (error) {
    const appError = handleApiError(error);
    
    if (errorHandler) {
      errorHandler(appError);
    } else {
      showErrorToast(appError);
    }
    
    return null;
  }
}

// Export a default object for easier imports
export default {
  createError,
  handleError,
  getUserFriendlyMessage,
  isRetryableError,
  createNetworkError,
  createTimeoutError,
  registerContextCollector,
  ErrorSeverity,
  ErrorCategory,
  AppError,
  ErrorCode,
  handleApiError,
  showErrorToast,
  withErrorHandling
}; 