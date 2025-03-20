/**
 * Utility functions for standardizing CORS and network resilience across API requests
 */
import axios from 'axios';
import { config } from '../config';
import { logger } from '../src/utils/logger';

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
      logger.info(`Request failed, retrying (${attempt + 1}/${maxRetries})...`, error);
      
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
 * @param {string} baseEndpoint - The API endpoint name (e.g., 'upload', 'generate') or full base URL
 * @param {Object} defaultOptions - Default options for all requests
 * @param {number} defaultOptions.retries - Default number of retries
 * @param {number} defaultOptions.retryDelay - Default delay between retries
 * @param {number} defaultOptions.timeout - Default timeout in milliseconds
 * @returns {Object} An object with helper methods for API requests
 */
export function createApiClient(baseEndpoint, defaultOptions = {}) {
  let baseUrl;
  
  // If baseEndpoint is a full URL, use it directly
  if (baseEndpoint.startsWith('http')) {
    baseUrl = baseEndpoint;
  } 
  // If it's a relative URL, prepend the API_URL
  else if (baseEndpoint.startsWith('/')) {
    baseUrl = `${config.API_URL}${baseEndpoint}`;
  }
  // Otherwise treat it as an endpoint key from the config
  else {
    baseUrl = config.endpoints[baseEndpoint];
    
    if (!baseUrl) {
      logger.error(`No endpoint configured for '${baseEndpoint}'`);
      // Fallback to API_URL as base
      baseUrl = `${config.API_URL}/${baseEndpoint}`;
    }
  }
  
  // Default configuration options
  const defaults = {
    retries: defaultOptions.retries || 3,
    retryDelay: defaultOptions.retryDelay || 1000,
    timeout: defaultOptions.timeout || 60000
  };
  
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
      
      // Merge default timeout with request options
      const mergedOptions = {
        ...requestOptions,
        timeout: requestOptions.timeout || defaults.timeout
      };
      
      // Merge default retry options with provided ones
      const mergedRetryOptions = {
        maxRetries: defaults.retries,
        retryDelay: defaults.retryDelay,
        ...retryOptions
      };
      
      return withRetry(
        () => axios.get(url, createRequestConfig(mergedOptions)),
        mergedRetryOptions
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
      
      // Merge default timeout with request options
      const mergedOptions = {
        ...requestOptions,
        timeout: requestOptions.timeout || defaults.timeout
      };
      
      // Merge default retry options with provided ones
      const mergedRetryOptions = {
        maxRetries: defaults.retries,
        retryDelay: defaults.retryDelay,
        ...retryOptions
      };
      
      return withRetry(
        () => axios.post(url, data, createRequestConfig(mergedOptions)),
        mergedRetryOptions
      );
    },
    
    /**
     * Make a PUT request with automatic retries
     * 
     * @param {string} path - Path to append to the base URL
     * @param {Object} data - Request payload
     * @param {Object} options - Request options and retry config
     * @returns {Promise} The API response
     */
    put: async (path, data, options = {}) => {
      const { retryOptions, ...requestOptions } = options;
      const url = path ? `${baseUrl}${path}` : baseUrl;
      
      // Merge default timeout with request options
      const mergedOptions = {
        ...requestOptions,
        timeout: requestOptions.timeout || defaults.timeout
      };
      
      // Merge default retry options with provided ones
      const mergedRetryOptions = {
        maxRetries: defaults.retries,
        retryDelay: defaults.retryDelay,
        ...retryOptions
      };
      
      return withRetry(
        () => axios.put(url, data, createRequestConfig(mergedOptions)),
        mergedRetryOptions
      );
    },
    
    /**
     * Make a DELETE request with automatic retries
     * 
     * @param {string} path - Path to append to the base URL
     * @param {Object} options - Request options and retry config
     * @returns {Promise} The API response
     */
    delete: async (path, options = {}) => {
      const { retryOptions, ...requestOptions } = options;
      const url = path ? `${baseUrl}${path}` : baseUrl;
      
      // Merge default timeout with request options
      const mergedOptions = {
        ...requestOptions,
        timeout: requestOptions.timeout || defaults.timeout
      };
      
      // Merge default retry options with provided ones
      const mergedRetryOptions = {
        maxRetries: defaults.retries,
        retryDelay: defaults.retryDelay,
        ...retryOptions
      };
      
      return withRetry(
        () => axios.delete(url, createRequestConfig(mergedOptions)),
        mergedRetryOptions
      );
    }
  };
} 