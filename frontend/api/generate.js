import axios from "axios";
import { config } from "../config";
import { handleApiError, formatApiError } from "../utils/errorHandler";

/**
 * Generate a report from uploaded documents
 * 
 * @param {number} reportId - ID of the report to generate content for
 * @param {Object} options - Additional options for generation
 * @returns {Promise<Object>} Generated report content
 */
export async function generateReport(reportId, options = {}) {
  try {
    console.log("Generating report with ID:", reportId);
    
    const payload = {
      report_id: reportId,
      ...options
    };
    
    // Use the configured API URL from config
    const response = await axios.post(`${config.endpoints.generate}/from-id`, payload);
    
    console.log("Generate API response status:", response.status);
    
    // Ensure response.data contains a content field
    if (!response.data.content) {
      console.warn("API response is missing content field:", response.data);
      // If there's no content field but there's a response, try to adapt it
      if (typeof response.data === 'string') {
        return { content: response.data };
      }
      
      // If it's an object with an output field
      if (response.data.output) {
        return { content: response.data.output };
      }
      
      // If it still doesn't have content, return a fallback
      return {
        content: "Failed to generate report content. Please try again."
      };
    }
    
    return response.data;
  } catch (error) {
    // Log the error but don't throw - return a fallback response
    console.error("Error generating report:", error);
    
    // More detailed logging for API errors
    if (error?.isAxiosError && error.response) {
      console.error("Server error response:", error.response.data);
    }
    
    // Create a user-friendly error message
    const errorMessage = formatApiError(error, "Error generating report");
    
    // Return a fallback response instead of throwing
    return {
      content: `${errorMessage}\n\nPlease try again later.`,
      error: true
    };
  }
}

/**
 * Request AI-based refinement of a report
 * 
 * @param {number} reportId - ID of the report to refine
 * @param {string} instructions - User instructions for refinement
 * @returns {Promise<Object>} Refined report content
 */
export async function refineReport(reportId, instructions) {
  try {
    console.log(`Refining report ${reportId} with instructions: ${instructions}`);
    
    const response = await axios.post(`${config.endpoints.generate}/refine`, {
      report_id: reportId,
      instructions: instructions
    });
    
    return response.data;
  } catch (error) {
    // Log error but provide fallback content
    console.error("Error refining report:", error);
    
    // Return fallback with error flag instead of throwing
    return {
      content: "Error refining report. Please try again with different instructions.",
      error: true
    };
  }
} 