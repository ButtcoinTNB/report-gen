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