import { Report } from '../src/types';
import config from '../config';
import { handleApiError } from "../utils/errorHandler";

/**
 * Fetch a report by its ID
 * 
 * @param {string} reportId - UUID of the report to fetch
 * @returns {Promise<Report>} The report data
 */
export async function getReport(reportId) {
    const response = await fetch(`${config.endpoints.reports}/${reportId}`);
    if (!response.ok) {
        throw new Error('Failed to fetch report');
    }
    return response.json();
}

/**
 * Update a report's content
 * 
 * @param {string} reportId - UUID of the report to update
 * @param {object} data - The data to update
 * @returns {Promise<Report>} The updated report
 */
export async function updateReport(reportId, data) {
    const response = await fetch(`${config.endpoints.reports}/${reportId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!response.ok) {
        throw new Error('Failed to update report');
    }
    return response.json();
}

/**
 * Refine a report based on user instructions
 * 
 * @param {string} reportId - UUID of the report to refine
 * @param {string} instructions - User instructions for refinement
 * @returns {Promise<Report>} The refined report
 */
export async function refineReport(reportId, instructions) {
    console.log(`Refining report ${reportId} with instructions: ${instructions}`);
    
    const response = await fetch(`${config.endpoints.reports}/${reportId}/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            report_id: reportId,
            instructions 
        })
    });
    
    if (!response.ok) {
        throw new Error('Failed to refine report');
    }
    
    return response.json();
}

/**
 * Check if a report exists and is ready
 * 
 * @param {string} reportId - UUID of the report to check
 * @returns {Promise<boolean>} Whether the report exists and is ready
 */
export async function checkReportExists(reportId) {
    try {
        const response = await fetch(`${config.endpoints.reports}/${reportId}/status`);
        if (!response.ok) {
            return false;
        }
        const data = await response.json();
        return data.exists && data.ready;
    } catch (error) {
        console.error('Error checking report status:', error);
        return false;
    }
}

/**
 * Download a report in the specified format
 * 
 * @param {string} reportId - UUID of the report to download
 * @param {string} format - Format to download (pdf, docx)
 * @returns {Promise<Blob>} The report file as a blob
 */
export async function downloadReport(reportId, format = 'docx') {
    const response = await fetch(`${config.endpoints.reports}/${reportId}/download?format=${format}`);
    if (!response.ok) {
        throw new Error('Failed to download report');
    }
    return response.blob();
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
    
    const response = await fetch(`${config.endpoints.reports}/${data.id}/finalize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error('Failed to finalize report');
    }
    
    return response.json();
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
    
    const response = await fetch(`${config.endpoints.reports}/templates`);
    if (!response.ok) {
      throw new Error('Failed to fetch templates');
    }
    return response.json();
  } catch (error) {
    return handleApiError(error, "fetching templates");
  }
}

/**
 * Check the status of a report
 * 
 * @param {string} reportId - UUID of the report to check
 * @returns {Promise<Object>} Report status
 */
export async function checkReportStatus(reportId) {
  try {
    console.log(`Checking status of report ${reportId}`);
    
    const response = await fetch(`${config.endpoints.reports}/${reportId}/status`);
    if (!response.ok) {
      throw new Error('Failed to check report status');
    }
    return response.json();
  } catch (error) {
    return handleApiError(error, "checking report status", { throwError: false });
  }
} 