import axios from "axios";
import { config } from "../config";
import { handleApiError, formatApiError } from "../utils/errorHandler";
import { Report, AnalysisResponse } from '../src/types';

/**
 * Analyze uploaded documents to extract information
 * 
 * @param {string} reportId - UUID of the report to analyze
 * @param {string} additionalInfo - Additional information for the analysis
 * @returns {Promise<AnalysisResponse>} Analysis results
 */
export async function analyzeDocuments(reportId, additionalInfo = "") {
  try {
    console.log("Analyzing documents for report ID:", reportId);
    
    // Ensure we have a valid report ID
    if (!reportId) {
      throw new Error("Report ID is required for document analysis");
    }
    
    const payload = { 
      report_id: reportId, // Add required report_id
      document_ids: [reportId], // Keep document_ids as before
      additional_info: additionalInfo
    };
    
    console.log("Analysis payload:", payload);
    
    const response = await axios.post(`${config.endpoints.generate}/analyze`, payload, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      withCredentials: false
    });
    
    console.log("Analysis API response:", response.data);
    
    return response.data;
  } catch (error) {
    console.error("Error analyzing documents:", error);
    
    if (error?.isAxiosError && error.response) {
      console.error("Server error response:", error.response.data);
    }
    
    const errorMessage = formatApiError(error, "Error analyzing documents");
    throw new Error(errorMessage);
  }
}

/**
 * Generate a report from uploaded documents with additional information
 * 
 * @param {string} reportId - UUID of the report to generate
 * @param {string} additionalInfo - Additional information for the report
 * @param {Function} onProgress - Optional callback for progress updates
 * @returns {Promise<Report>} The generated report
 */
export async function generateReportWithInfo(reportId, additionalInfo = "", onProgress) {
  try {
    console.log("Generating report with ID:", reportId);
    
    if (onProgress) {
      onProgress({ 
        step: 0, 
        message: "Analyzing documents 📄", 
        progress: 30
      });
    }
    
    const payload = {
      report_id: reportId,  // Add this to match the backend endpoint
      document_ids: [reportId],
      additional_info: additionalInfo
    };
    
    console.log("Generate payload:", payload);
    
    const response = await axios.post(`${config.endpoints.generate}/generate`, payload, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      withCredentials: false
    });
    
    console.log("Generate API response:", response.data);
    
    if (onProgress) {
      onProgress({ 
        step: 1, 
        message: "Report generated successfully ✅", 
        progress: 100
      });
    }
    
    return response.data;
  } catch (error) {
    console.error("Error generating report:", error);
    
    if (error?.isAxiosError && error.response) {
      console.error("Server error response:", error.response.data);
    }
    
    const errorMessage = formatApiError(error, "Error generating report");
    throw new Error(errorMessage);
  }
}

/**
 * Generate a report from uploaded documents
 * 
 * @param {string} reportId - UUID of the report to generate content for
 * @param {object} options - Generation options
 * @param {Function} onProgress - Optional callback for progress updates
 * @returns {Promise<Report>} The generated report content
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
    console.error("Error generating report:", error);
    throw new Error(error.message || "Failed to generate report");
  }
}

/**
 * Request AI-based refinement of a report
 * 
 * @param {string} reportId - UUID of the report to refine
 * @param {string} instructions - User instructions for refinement
 * @param {Function} onProgress - Optional callback for progress updates
 * @returns {Promise<Report>} The refined report
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
    
    const response = await axios.post(`${config.endpoints.generate}/reports/${reportId}/refine`, {
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