/**
 * Shared error handling utilities for API requests
 */

/**
 * Format an error from an API request into a user-friendly message
 * 
 * @param {Error} error - The error object from the API request
 * @param {string} fallbackMessage - A fallback message if the error can't be parsed
 * @returns {string} A user-friendly error message
 */
export function formatApiError(error, fallbackMessage = "An unexpected error occurred") {
  // Check if it's an Axios error
  if (error && error.isAxiosError) {
    if (error.response) {
      // Server responded with error
      const { status, data } = error.response;
      
      // Handle different status codes
      if (status === 413) {
        return "File too large. Please try a smaller file.";
      }
      
      if (status === 422) {
        return "Invalid data provided. Please check your inputs.";
      }
      
      // Handle common error response formats
      if (data) {
        if (data.detail) {
          return `Error: ${data.detail}`;
        }
        if (data.message) {
          return `Error: ${data.message}`;
        }
        if (typeof data === 'string') {
          return `Error: ${data}`;
        }
      }
      
      return `Server error (${status})`;
    } 
    
    if (error.request) {
      // Request made but no response received
      return "No response from server. Check your internet connection.";
    }
  }
  
  // For non-axios errors or unhandled error types
  return error?.message || fallbackMessage;
}

/**
 * Handle common API errors with standard logging
 * 
 * @param {Error} error - The error object
 * @param {string} context - Description of where the error occurred
 * @param {Object} options - Additional options
 * @returns {string} A formatted error message
 */
export function handleApiError(error, context, { log = true, throwError = true } = {}) {
  if (log) {
    console.error(`Error in ${context}:`, error);
    
    // Log additional details for Axios errors
    if (error?.isAxiosError && error.response) {
      console.error("Response status:", error.response.status);
      console.error("Response data:", error.response.data);
    }
  }
  
  const errorMessage = formatApiError(error, `Error in ${context}`);
  
  if (throwError) {
    throw new Error(errorMessage);
  }
  
  return errorMessage;
} 