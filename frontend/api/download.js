import axios from "axios";
import { config } from "../config";
import { handleApiError } from "../utils/errorHandler";

/**
 * Download a report PDF directly
 * 
 * @param {number} reportId - ID of the report to download
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
 * @param {number} reportId - ID of the report
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
 * @param {number} reportId - ID of the report to clean up
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
 * @param {number} reportId - ID of the report to download
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
 * @param {number} reportId - ID of the report to convert
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