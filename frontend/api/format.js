import axios from "axios";
import { config } from "../config";
import { handleApiError } from "../utils/errorHandler";

/**
 * Format a report as PDF with preview or final mode
 * 
 * @param {number} reportId - ID of the report to format
 * @param {boolean} isPreview - Whether this is a preview (true) or final version (false)
 * @returns {Promise<Object>} Formatting response
 */
export async function formatReport(reportId, isPreview) {
  try {
    const endpoint = isPreview ? "preview" : "final";
    console.log(`Formatting report ${reportId} as ${endpoint} at ${config.endpoints.format}/${endpoint}`);
    
    const response = await axios.post(`${config.endpoints.format}/${endpoint}`, {
      report_id: reportId
    });

    // For preview, the response contains a PDF file, so handle it accordingly
    if (isPreview) {
      // Create a temporary link to open the PDF in a new tab
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');
    }

    return response.data;
  } catch (error) {
    return handleApiError(error, "report formatting");
  }
} 