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
    
    // First get the report metadata and download URL
    const response = await axios.get(`${config.endpoints.download}/${reportId}`, {
      timeout: 10000 // 10 second timeout
    });
    
    console.log("Download response:", response.data);
    
    // Construct full URL for download including host
    let downloadUrl = response.data.download_url;
    
    // If the URL doesn't include the protocol and host, add it
    if (downloadUrl && downloadUrl.startsWith('/api/')) {
      downloadUrl = `${config.API_URL}${downloadUrl}`;
    }
    
    return {
      data: {
        ...response.data,
        download_url: downloadUrl
      },
      status: response.status
    };
  } catch (error) {
    console.error("Error downloading report:", error);
    if (error.response) {
      console.error("Server responded with error:", error.response.data);
      console.error("Status code:", error.response.status);
      throw new Error(`Server error (${error.response.status}): ${JSON.stringify(error.response.data)}`);
    } else if (error.request) {
      console.error("No response received:", error.request);
      throw new Error("No response received from server");
    } else {
      throw error;
    }
  }
} 