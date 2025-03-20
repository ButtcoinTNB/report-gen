import axios from "axios";
import { config } from "../config";
import { handleApiError, formatApiError } from "../utils/errorHandler";
import { 
  createRequestConfig,
  withRetry,
  createApiClient
} from "../utils/corsHelper";
import { Report, AnalysisResponse } from '../src/types';

// Create API client for generation endpoints
const generateApi = createApiClient('generate');

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
    
    // Use our generateApi client with retry functionality
    const response = await generateApi.post('/analyze', payload, {
      retryOptions: {
        maxRetries: 2,
        retryDelay: 1500
      }
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
    console.log("Generating report with info for report ID:", reportId);
    
    // Ensure we have a valid report ID
    if (!reportId) {
      throw new Error("Report ID is required for report generation");
    }
    
    const payload = { 
      report_id: reportId,
      document_ids: [reportId],
      additional_info: additionalInfo
    };
    
    console.log("Generation payload:", payload);
    
    // Update progress if callback provided
    if (onProgress) {
      onProgress({ stage: 'generating', progress: 10 });
    }
    
    // Use our generateApi client with retry functionality
    const response = await generateApi.post('/generate', payload, {
      retryOptions: {
        maxRetries: 3,
        retryDelay: 2000,
        onRetry: (attempt) => {
          console.log(`Generation retry attempt ${attempt}`);
          if (onProgress) {
            onProgress({ stage: 'retrying', attempt, progress: 10 + (attempt * 5) });
          }
        }
      }
    });
    
    // Update progress if callback provided
    if (onProgress) {
      onProgress({ stage: 'completed', progress: 100 });
    }
    
    console.log("Generation API response:", response.data);
    
    return response.data;
  } catch (error) {
    console.error("Error generating report with info:", error);
    
    if (error?.isAxiosError && error.response) {
      console.error("Server error response:", error.response.data);
    }
    
    // Update progress if callback provided
    if (onProgress) {
      onProgress({ stage: 'error', progress: 0 });
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
    console.log("Generating report from ID:", reportId);
    
    const payload = { 
      report_id: reportId,
      ...options
    };
    
    // Update progress if callback provided
    if (onProgress) {
      onProgress({ stage: 'generating', progress: 10 });
    }
    
    // Use our generateApi client with retry functionality
    const response = await generateApi.post('/from-id', payload, {
      retryOptions: {
        maxRetries: 3,
        retryDelay: 2000,
        onRetry: (attempt) => {
          console.log(`Generation retry attempt ${attempt}`);
          if (onProgress) {
            onProgress({ stage: 'retrying', attempt, progress: 10 + (attempt * 5) });
          }
        }
      }
    });
    
    // Update progress if callback provided
    if (onProgress) {
      onProgress({ stage: 'completed', progress: 100 });
    }
    
    return response.data;
  } catch (error) {
    console.error("Error generating report from ID:", error);
    
    // Update progress if callback provided
    if (onProgress) {
      onProgress({ stage: 'error', progress: 0 });
    }
    
    const errorMessage = formatApiError(error, "Error generating report");
    throw new Error(errorMessage);
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
    console.log("Refining report:", reportId);
    
    const payload = { instructions };
    
    // Update progress if callback provided
    if (onProgress) {
      onProgress({ stage: 'refining', progress: 10 });
    }
    
    // Use our generateApi client with retry functionality
    const response = await generateApi.post(`/reports/${reportId}/refine`, payload, {
      retryOptions: {
        maxRetries: 2,
        onRetry: (attempt) => {
          console.log(`Refinement retry attempt ${attempt}`);
          if (onProgress) {
            onProgress({ stage: 'retrying', attempt, progress: 10 + (attempt * 5) });
          }
        }
      }
    });
    
    // Update progress if callback provided
    if (onProgress) {
      onProgress({ stage: 'completed', progress: 100 });
    }
    
    return response.data;
  } catch (error) {
    console.error("Error refining report:", error);
    
    // Update progress if callback provided
    if (onProgress) {
      onProgress({ stage: 'error', progress: 0 });
    }
    
    const errorMessage = formatApiError(error, "Error refining report");
    throw new Error(errorMessage);
  }
} 