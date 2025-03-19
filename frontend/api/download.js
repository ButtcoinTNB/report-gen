import axios from "axios";
import { config } from "../config";
import { handleApiError } from "../utils/errorHandler";

/**
 * Get a preview of the report PDF
 * 
 * @param {string|number} reportId - ID of the report to preview (UUID or integer)
 * @returns {Promise<Object>} Preview information including URL
 */
export async function fetchPDFPreview(reportId) {
  try {
    console.log(`Generating PDF preview for report ${reportId}`);
    
    // First, tell the server to generate a preview
    const response = await axios.post(`${config.endpoints.format}/preview-file`, {
      report_id: reportId
    });
    
    // The response should include a URL to view the preview
    if (response.data && response.data.preview_url) {
      return {
        success: true,
        previewUrl: `${config.API_URL}${response.data.preview_url}`,
        previewId: response.data.preview_id
      };
    } else {
      console.error("Invalid preview response:", response.data);
      throw new Error("Failed to generate preview");
    }
  } catch (error) {
    return handleApiError(error, "PDF preview generation", { throwError: true });
  }
}

/**
 * Download a report PDF directly
 * 
 * @param {string|number} reportId - ID of the report to download (UUID or integer)
 * @returns {Promise<boolean>} Success status
 */
export async function downloadPDF(reportId) {
  try {
    console.log(`Downloading PDF for report ${reportId} from ${config.endpoints.download}/${reportId}`);
    
    const response = await axios.get(`${config.endpoints.download}/${reportId}`, {
      responseType: "blob",
    });

    // Create a Blob URL and trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `report_${reportId}.pdf`);
    document.body.appendChild(link);
    link.click();
    
    // After successful download, clean up server files
    try {
      await cleanupReportFiles(reportId);
      console.log("Cleanup completed for report files");
    } catch (cleanupError) {
      console.warn("Failed to clean up report files:", cleanupError);
      // Don't throw the error as the download was still successful
    }

    return true;
  } catch (error) {
    return handleApiError(error, "PDF download");
  }
}

/**
 * Get download information for a report
 * 
 * @param {string|number} reportId - ID of the report (UUID or integer)
 * @returns {Promise<Object>} Download information
 */
export async function downloadReport(reportId) {
  try {
    console.log(`Getting download info for report ${reportId}`);
    
    const response = await axios.get(`${config.endpoints.download}/${reportId}`);
    return response.data;
  } catch (error) {
    return handleApiError(error, "getting download information");
  }
}

/**
 * Clean up report files after download
 * 
 * @param {string|number} reportId - ID of the report to clean up (UUID or integer)
 * @returns {Promise<Object>} Cleanup response
 */
export async function cleanupReportFiles(reportId) {
  try {
    console.log(`Cleaning up files for report ${reportId}`);
    
    const response = await axios.post(`${config.endpoints.download}/cleanup/${reportId}`);
    return response.data;
  } catch (error) {
    return handleApiError(error, "cleanup report files", { throwError: false });
  }
}

/**
 * Download a report in DOCX format
 * 
 * @param {string|number} reportId - ID of the report to download (UUID or integer)
 * @returns {Promise<boolean>} Success status
 */
export async function downloadDOCX(reportId) {
  try {
    console.log(`Downloading DOCX for report ${reportId}`);
    
    const response = await axios.get(`${config.endpoints.download}/docx/${reportId}`, {
      responseType: "blob",
    });

    // Create a Blob URL and trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `report_${reportId}.docx`);
    document.body.appendChild(link);
    link.click();

    return true;
  } catch (error) {
    return handleApiError(error, "DOCX download");
  }
}

/**
 * Generate a DOCX version of a report
 * 
 * @param {string|number} reportId - ID of the report to convert (UUID or integer)
 * @returns {Promise<Object>} Generation response
 */
export async function generateDOCX(reportId) {
  try {
    console.log(`Generating DOCX for report ${reportId}`);
    
    const response = await axios.post(`${config.endpoints.download}/generate-docx/${reportId}`);
    return response.data;
  } catch (error) {
    return handleApiError(error, "DOCX generation");
  }
}

/**
 * Get a preview of a report
 * 
 * @param {string} reportId - UUID of the report to preview
 * @returns {Promise<Blob>} The preview file as a blob
 */
export async function getPreview(reportId) {
    const response = await fetch(`${config.endpoints.reports}/${reportId}/preview`);
    if (!response.ok) {
        throw new Error('Failed to get preview');
    }
    return response.blob();
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
 * Clean up temporary files for a report
 * 
 * @param {string} reportId - UUID of the report to clean up
 * @returns {Promise<void>}
 */
export async function cleanupFiles(reportId) {
    const response = await fetch(`${config.endpoints.reports}/${reportId}/cleanup`, {
        method: 'POST'
    });
    if (!response.ok) {
        throw new Error('Failed to clean up files');
    }
} 