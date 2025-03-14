import axios from "axios";

export async function formatReport(reportId: number, isPreview: boolean) {
  try {
    const endpoint = isPreview ? "preview" : "final";
    const response = await axios.post(`http://localhost:8000/api/format/${endpoint}`, {
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