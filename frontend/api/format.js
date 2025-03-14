import axios from "axios";
import { config } from "../config";

export async function formatReport(reportId, isPreview) {
  try {
    const endpoint = isPreview ? "preview" : "final";
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
    console.error("Error formatting report:", error);
    throw error;
  }
} 