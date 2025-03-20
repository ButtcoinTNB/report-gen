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
        // Check for standardized error format first
        if (data.status === "error") {
          let errorMsg = data.message || "Unknown error";
          
          // Include operation context if available
          if (data.operation) {
            errorMsg = `Error during ${data.operation}: ${errorMsg}`;
          }
          
          // Include error type for more context if available
          if (data.error_type) {
            // Map technical error types to user-friendly descriptions
            const errorTypeMap = {
              "validation_error": "Validation failed",
              "value_error": "Invalid value",
              "key_error": "Missing required field",
              "file_not_found": "File not found",
              "permission_error": "Permission denied", 
              "not_implemented": "Feature not implemented",
              "timeout_error": "Operation timed out",
              "connection_error": "Connection failed",
              "internal_error": "Internal server error"
            };
            
            const readableType = errorTypeMap[data.error_type] || data.error_type;
            return `${readableType}: ${errorMsg}`;
          }
          
          return errorMsg;
        }
        
        // Fall back to other formats
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
      
      // Additional logging for standardized error format
      const data = error.response.data;
      if (data && data.status === "error") {
        console.error("Error type:", data.error_type);
        console.error("Operation:", data.operation);
        
        // Log traceback in development mode if available
        if (data.traceback && process.env.NODE_ENV !== 'production') {
          console.error("Traceback:", data.traceback);
        }
      }
    }
  }
  
  const errorMessage = formatApiError(error, `Error in ${context}`);
  
  if (throwError) {
    throw new Error(errorMessage);
  }
  
  return errorMessage;
} 