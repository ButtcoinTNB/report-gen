/**
 * Utility functions for standardizing CORS and network resilience across API requests
 */
import axios from 'axios';
import { config } from '../config';

/**
 * Standard headers for JSON API requests
 */
export const jsonHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
};

/**
 * Standard headers for multipart form data requests (file uploads)
 */
export const multipartHeaders = {
  'Content-Type': 'multipart/form-data',
  'Accept': 'application/json'
};

/**
 * Create an axios instance with standardized CORS settings
 * 
 * @param {Object} options - Configuration options
 * @param {boolean} options.isMultipart - Whether this is a multipart form request
 * @param {number} options.timeout - Request timeout in milliseconds
 * @param {Function} options.onUploadProgress - Upload progress callback
 * @returns {Object} Axios request configuration
 */
export function createRequestConfig({
  isMultipart = false,
  timeout = 60000,
  onUploadProgress = null
} = {}) {
  const requestConfig = {
    headers: isMultipart ? multipartHeaders : jsonHeaders,
    withCredentials: false, // Set to false when using "*" for allowed origins
    timeout: timeout,
  };

  // Add upload progress tracking for multipart requests if provided
  if (isMultipart && onUploadProgress) {
    requestConfig.onUploadProgress = onUploadProgress;
  }

  return requestConfig;
}

/**
 * Make a request with retry functionality for improved network resilience
 * 
 * @param {Function} requestFn - Function that returns a promise (axios request)
 * @param {Object} options - Options for the retry mechanism
 * @param {number} options.maxRetries - Maximum number of retry attempts
 * @param {number} options.retryDelay - Delay between retries in milliseconds
 * @param {Function} options.onRetry - Callback when a retry is attempted
 * @returns {Promise} The result of the request
 */
export async function withRetry(
  requestFn,
  {
    maxRetries = 3,
    retryDelay = 1000,
    onRetry = null
  } = {}
) {
  let lastError;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      // On first attempt or subsequent retries
      return await requestFn();
    } catch (error) {
      lastError = error;
      
      // Only retry on network errors or 5xx errors, not on 4xx client errors
      const shouldRetry = (
        error.code === 'ECONNABORTED' || 
        error.code === 'ERR_NETWORK' ||
        (error.response && error.response.status >= 500 && error.response.status < 600)
      );
      
      // If we've reached max retries or shouldn't retry this error, throw
      if (attempt >= maxRetries || !shouldRetry) {
        throw error;
      }
      
      // Log retry attempt
      console.log(`Request failed, retrying (${attempt + 1}/${maxRetries})...`, error);
      
      // Call onRetry callback if provided
      if (onRetry) {
        onRetry(attempt + 1, maxRetries);
      }
      
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, retryDelay * (attempt + 1)));
    }
  }
  
  // This should never be reached due to the throw in the loop
  throw lastError;
}

/**
 * Create a complete axios client with predefined backend URL and retry functionality
 * 
 * @param {string} baseEndpoint - The API endpoint name (e.g., 'upload', 'generate')
 * @returns {Object} An object with helper methods for API requests
 */
export function createApiClient(baseEndpoint) {
  const baseUrl = config.endpoints[baseEndpoint];
  
  if (!baseUrl) {
    console.error(`No endpoint configured for '${baseEndpoint}'`);
  }
  
  return {
    /**
     * Make a GET request with automatic retries
     * 
     * @param {string} path - Path to append to the base URL
     * @param {Object} options - Request options and retry config
     * @returns {Promise} The API response
     */
    get: async (path, options = {}) => {
      const { retryOptions, ...requestOptions } = options;
      const url = path ? `${baseUrl}${path}` : baseUrl;
      
      return withRetry(
        () => axios.get(url, createRequestConfig(requestOptions)),
        retryOptions
      );
    },
    
    /**
     * Make a POST request with automatic retries
     * 
     * @param {string} path - Path to append to the base URL
     * @param {Object} data - Request payload
     * @param {Object} options - Request options and retry config
     * @returns {Promise} The API response
     */
    post: async (path, data, options = {}) => {
      const { retryOptions, ...requestOptions } = options;
      const url = path ? `${baseUrl}${path}` : baseUrl;
      
      return withRetry(
        () => axios.post(url, data, createRequestConfig(requestOptions)),
        retryOptions
      );
    }
  };
} 