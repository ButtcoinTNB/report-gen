import axios from "axios";
import { config } from "../config";

export async function downloadPDF(reportId) {
  try {
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
    console.error("Error downloading report:", error);
    throw error;
  }
}

// Function to get the download URL without directly downloading
export async function downloadReport(reportId) {
  try {
    const response = await axios.get(`${config.endpoints.download}/${reportId}`);
    return response.data;
  } catch (error) {
    console.error("Error getting download URL:", error);
    throw error;
  }
}

// Function to clean up report files after download
export async function cleanupReportFiles(reportId) {
  try {
    const response = await axios.post(`${config.endpoints.download}/cleanup/${reportId}`);
    return response.data;
  } catch (error) {
    console.error("Error cleaning up report files:", error);
    throw error;
  }
} 