import axios from "axios";
import { config } from "../config";

/**
 * Fetch a report by ID
 */
export async function getReport(reportId) {
  try {
    const response = await axios.get(`${config.endpoints.edit}/${reportId}`);
    return response.data;
  } catch (error) {
    console.error("Error fetching report:", error);
    throw error;
  }
}

/**
 * Update a report with edited content
 */
export async function updateReport(reportId, data) {
  try {
    const response = await axios.put(`${config.endpoints.edit}/${reportId}`, data);
    return response.data;
  } catch (error) {
    console.error("Error updating report:", error);
    throw error;
  }
}

/**
 * Request AI refinement for a report
 */
export async function refineReport(reportId, instructions) {
  try {
    const response = await axios.post(`${config.endpoints.edit}/ai-refine`, {
      report_id: reportId,
      instructions: instructions
    });
    return response.data;
  } catch (error) {
    console.error("Error refining report:", error);
    throw error;
  }
}

/**
 * Finalize a report, creating the PDF
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
    console.error("Error finalizing report:", error);
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error("Server responded with error:", error.response.data);
      console.error("Status code:", error.response.status);
      throw new Error(`Server error (${error.response.status}): ${JSON.stringify(error.response.data)}`);
    } else if (error.request) {
      // The request was made but no response was received
      console.error("No response received:", error.request);
      throw new Error("No response received from server");
    } else {
      // Something happened in setting up the request that triggered an Error
      throw error;
    }
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