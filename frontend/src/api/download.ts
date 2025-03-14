import axios from "axios";

export async function downloadPDF(reportId: number) {
  try {
    const response = await axios.get(`http://localhost:8000/api/download/${reportId}`, {
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
