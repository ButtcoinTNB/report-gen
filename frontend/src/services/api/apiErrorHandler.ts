import { isServer } from '../../utils/environment';

/**
 * Error categories for better error handling
 */
export enum ErrorCategory {
  NETWORK = 'network',
  SERVER = 'server',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  VALIDATION = 'validation',
  NOT_FOUND = 'not_found',
  TIMEOUT = 'timeout',
  UNKNOWN = 'unknown',
}

/**
 * Standardized API error with rich information
 */
export class ApiError extends Error {
  public readonly category: ErrorCategory;
  public readonly status: number;
  public readonly isRetryable: boolean;
  public readonly originalError?: unknown;
  public readonly context?: Record<string, unknown>;
  public readonly requestId?: string;
  
  constructor({
    message,
    category = ErrorCategory.UNKNOWN,
    status = 500,
    isRetryable = false,
    originalError,
    context,
    requestId,
  }: {
    message: string;
    category?: ErrorCategory;
    status?: number;
    isRetryable?: boolean;
    originalError?: unknown;
    context?: Record<string, unknown>;
    requestId?: string;
  }) {
    super(message);
    this.name = 'ApiError';
    this.category = category;
    this.status = status;
    this.isRetryable = isRetryable;
    this.originalError = originalError;
    this.context = context;
    this.requestId = requestId;
    
    // Ensure proper prototype chain for instanceof checks
    Object.setPrototypeOf(this, ApiError.prototype);
  }
  
  /**
   * Get a user-friendly message based on the error category
   */
  getUserFriendlyMessage(): string {
    switch (this.category) {
      case ErrorCategory.NETWORK:
        return 'Network error: Please check your internet connection and try again.';
      case ErrorCategory.AUTHENTICATION:
        return 'Authentication error: Please log in again.';
      case ErrorCategory.AUTHORIZATION:
        return 'Authorization error: You do not have permission to perform this action.';
      case ErrorCategory.VALIDATION:
        return 'Validation error: Please check your input and try again.';
      case ErrorCategory.NOT_FOUND:
        return 'Resource not found: The requested resource was not found.';
      case ErrorCategory.TIMEOUT:
        return 'Request timeout: The operation took too long to complete. Please try again.';
      case ErrorCategory.SERVER:
        return 'Server error: Something went wrong on our end. Please try again later.';
      default:
        return this.message || 'An unexpected error occurred. Please try again.';
    }
  }
  
  /**
   * Get technical details for debugging
   */
  getTechnicalDetails(): string {
    return JSON.stringify({
      category: this.category,
      status: this.status,
      message: this.message,
      isRetryable: this.isRetryable,
      requestId: this.requestId,
      context: this.context,
      originalError: this.originalError instanceof Error 
        ? {
            name: this.originalError.name,
            message: this.originalError.message,
            stack: isServer ? this.originalError.stack : undefined
          }
        : this.originalError
    }, null, 2);
  }
}

/**
 * Categorize HTTP errors by status code
 */
export function categorizeHttpError(status: number): ErrorCategory {
  if (status >= 500) return ErrorCategory.SERVER;
  if (status === 401) return ErrorCategory.AUTHENTICATION;
  if (status === 403) return ErrorCategory.AUTHORIZATION;
  if (status === 404) return ErrorCategory.NOT_FOUND;
  if (status === 422) return ErrorCategory.VALIDATION;
  if (status >= 400 && status < 500) return ErrorCategory.VALIDATION;
  return ErrorCategory.UNKNOWN;
}

/**
 * Determine if an error is retryable
 */
export function isRetryableError(error: unknown): boolean {
  // ApiErrors self-identify if they're retryable
  if (error instanceof ApiError) {
    return error.isRetryable;
  }
  
  // Network errors are usually retryable
  if (error instanceof TypeError && error.message.includes('Network')) {
    return true;
  }
  
  // Timeouts are retryable
  if (error instanceof Error && error.message.includes('timeout')) {
    return true;
  }
  
  return false;
}

/**
 * Convert any error to a standard ApiError
 */
export function normalizeError(error: unknown): ApiError {
  // If it's already an ApiError, return it
  if (error instanceof ApiError) {
    return error;
  }
  
  // Handle fetch Response objects
  if (typeof Response !== 'undefined' && error instanceof Response) {
    const category = categorizeHttpError(error.status);
    const isRetryable = error.status >= 500 || error.status === 0;
    
    return new ApiError({
      message: `HTTP Error ${error.status}: ${error.statusText}`,
      category,
      status: error.status,
      isRetryable,
      originalError: error,
      requestId: error.headers.get('x-request-id') || undefined
    });
  }
  
  // Handle other errors
  if (error instanceof Error) {
    const isNetwork = error.message.includes('Network') || error.message.includes('fetch');
    const isTimeout = error.message.includes('timeout');
    
    let category = ErrorCategory.UNKNOWN;
    if (isNetwork) category = ErrorCategory.NETWORK;
    if (isTimeout) category = ErrorCategory.TIMEOUT;
    
    return new ApiError({
      message: error.message,
      category,
      isRetryable: isNetwork || isTimeout,
      originalError: error
    });
  }
  
  // Handle non-Error objects
  return new ApiError({
    message: typeof error === 'string' ? error : 'Unknown error occurred',
    category: ErrorCategory.UNKNOWN,
    originalError: error
  });
}

/**
 * Enhance any async function with standardized error handling
 */
export function withErrorHandling<T extends (...args: any[]) => Promise<any>>(
  fn: T
): (...args: Parameters<T>) => Promise<Awaited<ReturnType<T>>> {
  return async (...args: Parameters<T>): Promise<Awaited<ReturnType<T>>> => {
    try {
      return await fn(...args);
    } catch (error) {
      throw normalizeError(error);
    }
  };
}

export default {
  ApiError,
  ErrorCategory,
  categorizeHttpError,
  isRetryableError,
  normalizeError,
  withErrorHandling
}; 