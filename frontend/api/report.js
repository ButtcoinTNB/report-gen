import axios from "axios";
import { config } from "../config";
import { handleApiError } from "../utils/errorHandler";

/**
 * Fetch a report by ID
 * 
 * @param {number} reportId - ID of the report to fetch
 * @returns {Promise<Object>} Report data
 */
export async function getReport(reportId) {
  try {
    console.log(`Fetching report with ID: ${reportId}`);
    
    const response = await axios.get(`${config.endpoints.edit}/${reportId}`);
    return response.data;
  } catch (error) {
    return handleApiError(error, "fetching report");
  }
}

/**
 * Update a report with edited content
 * 
 * @param {number} reportId - ID of the report to update
 * @param {Object} data - Data to update (content, title, etc.)
 * @returns {Promise<Object>} Updated report data
 */
export async function updateReport(reportId, data) {
  try {
    console.log(`Updating report ${reportId} with data:`, data);
    
    const response = await axios.put(`${config.endpoints.edit}/${reportId}`, data);
    return response.data;
  } catch (error) {
    return handleApiError(error, "updating report");
  }
}

/**
 * Request AI refinement for a report
 * 
 * @param {number} reportId - ID of the report to refine
 * @param {string} instructions - Instructions for AI refinement
 * @returns {Promise<Object>} Refined report data
 */
export async function refineReport(reportId, instructions) {
  try {
    console.log(`Refining report ${reportId} with instructions: ${instructions}`);
    
    const response = await axios.post(`${config.endpoints.edit}/ai-refine`, {
      report_id: reportId,
      instructions: instructions
    });
    return response.data;
  } catch (error) {
    return handleApiError(error, "AI refinement");
  }
}

/**
 * Finalize a report, creating the PDF
 * 
 * @param {Object} data - Report data including ID and template ID
 * @returns {Promise<Object>} Finalized report data
 */
export async function finalizeReport(data) {
  try {
    console.log("Finalizing report with data:", data);
    
    const response = await axios.post(`${config.endpoints.format}/final`, data, {
      timeout: 30000 // Increase timeout to 30 seconds as PDF generation might take time
    });
    
    console.log("Finalize response:", response.data);
    return response.data;
  } catch (error) {
    return handleApiError(error, "finalizing report");
  }
}

/**
 * Get available templates
 * 
 * @returns {Promise<Array>} List of available templates
 */
export async function getTemplates() {
  try {
    console.log("Fetching available templates");
    
    const response = await axios.get(`${config.endpoints.upload}/templates`);
    return response.data;
  } catch (error) {
    return handleApiError(error, "fetching templates");
  }
}

/**
 * Check the status of a report
 * 
 * @param {number} reportId - ID of the report to check
 * @returns {Promise<Object>} Report status
 */
export async function checkReportStatus(reportId) {
  try {
    console.log(`Checking status of report ${reportId}`);
    
    const response = await axios.get(`${config.endpoints.edit}/status/${reportId}`);
    return response.data;
  } catch (error) {
    return handleApiError(error, "checking report status", { throwError: false });
  }
}

/**
 * Download a finalized report
 */
export async function downloadReport(reportId) {
  try {
    console.log("Downloading report with ID:", reportId);
    
    // Direct download approach - create a download URL and trigger browser download
    const directUrl = `${config.API_URL}/api/download/${reportId}`;
    console.log("Using direct download URL:", directUrl);
    
    // Return the direct URL to be opened in a new tab/window
    return {
      data: {
        download_url: directUrl
      },
      status: 200
    };
  } catch (error) {
    console.error("Error preparing download:", error);
    throw new Error(`Failed to prepare download: ${error.message}`);
  }
} 