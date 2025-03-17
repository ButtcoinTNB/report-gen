import axios from "axios";
import { config } from "../config";
import { handleApiError, formatApiError } from "../utils/errorHandler";

/**
 * Get a brief AI summary of uploaded documents
 * 
 * @param {number} reportId - ID of the report to summarize
 * @param {Function} onProgress - Optional callback for progress updates
 * @returns {Promise<Object>} Summary and key facts
 */
export async function getSummary(reportId, onProgress) {
  try {
    console.log("Getting summary for report ID:", reportId);
    
    // Let the UI know we're starting
    if (onProgress) {
      onProgress({ 
        step: 0, 
        message: "Analyzing documents 🔍", 
        progress: 50 
      });
    }
    
    const payload = { report_id: reportId };
    
    // Use the configured API URL from config
    const response = await axios.post(`${config.endpoints.generate}/summarize`, payload);
    
    console.log("Summary API response:", response.data);
    
    // Let the UI know we're completed
    if (onProgress) {
      onProgress({ 
        step: 1, 
        message: "Analysis complete ✅", 
        progress: 100 
      });
    }
    
    // Return the summary data
    return {
      summary: response.data.summary || "No summary available",
      keyFacts: response.data.key_facts || [],
      error: false
    };
  } catch (error) {
    console.error("Error getting summary:", error);
    
    // More detailed logging for API errors
    if (error?.isAxiosError && error.response) {
      console.error("Server error response:", error.response.data);
    }
    
    // Create a user-friendly error message
    const errorMessage = formatApiError(error, "Error analyzing documents");
    
    return {
      summary: "Unable to generate summary. Please try again.",
      keyFacts: [],
      error: true,
      errorMessage
    };
  }
}

/**
 * Generate a report from uploaded documents
 * 
 * @param {number} reportId - ID of the report to generate content for
 * @param {Object} options - Additional options for generation
 * @param {Function} onProgress - Optional callback for progress updates
 * @returns {Promise<Object>} Generated report content
 */
export async function generateReport(reportId, options = {}, onProgress) {
  try {
    console.log("Generating report with ID:", reportId);
    
    const payload = {
      report_id: reportId,
      ...options
    };
    
    // Let the UI know we're starting
    if (onProgress) {
      onProgress({ 
        step: 0, 
        message: "Extracting content 📄", 
        progress: 30
      });
    }
    
    // Use the configured API URL from config
    const response = await axios.post(`${config.endpoints.generate}/from-id`, payload);
    
    console.log("Generate API response status:", response.status);
    
    // Let the UI know we're completed
    if (onProgress) {
      onProgress({ 
        step: 3, 
        message: "Done! Reviewing your report... ✅", 
        progress: 100
      });
    }
    
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
 * @param {Function} onProgress - Optional callback for progress updates
 * @returns {Promise<Object>} Refined report content
 */
export async function refineReport(reportId, instructions, onProgress) {
  try {
    console.log(`Refining report ${reportId} with instructions: ${instructions}`);
    
    // Let the UI know we're starting
    if (onProgress) {
      onProgress({ 
        step: 0, 
        message: "Analyzing your report 📑", 
        progress: 30
      });
    }
    
    const response = await axios.post(`${config.endpoints.generate}/refine`, {
      report_id: reportId,
      instructions: instructions
    });
    
    // Let the UI know we're completed
    if (onProgress) {
      onProgress({ 
        step: 2, 
        message: "Refinement complete ✅", 
        progress: 100
      });
    }
    
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