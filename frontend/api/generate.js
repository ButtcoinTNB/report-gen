import axios from "axios";
import { config } from "../config.js";

/**
 * Generate a report from uploaded documents
 */
export async function generateReport(reportId) {
  try {
    console.log("Calling generate API with report ID:", reportId);
    
    // Use the configured API URL from config instead of hardcoded localhost
    const response = await axios.post(`${config.endpoints.generate}/from-id`, {
      report_id: reportId
    });
    
    console.log("Generate API response:", response);
    console.log("Generate API response data:", response.data);
    
    // Ensure response.data contains a content field
    if (!response.data.content) {
      console.error("API response is missing content field:", response.data);
      // If there's no content field but there's a response, try to adapt it
      if (typeof response.data === 'string') {
        return { content: response.data };
      }
      
      // If it still doesn't have content, return a fallback
      return {
        content: "Failed to generate report content. Please try again."
      };
    }
    
    return response.data;
  } catch (error) {
    console.error("Error generating report:", error);
    if (axios.isAxiosError && error.response) {
      console.error("Server error response:", error.response.data);
    }
    
    // Return a fallback response instead of throwing
    return {
      content: "Error generating report. Please try again later."
    };
  }
} 