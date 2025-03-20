import { corsHelper } from '../../utils/corsHelper';
import { Report } from '../../types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const downloadApi = {
  // Get a URL for previewing the report
  getPreviewUrl: (reportId: string, format: 'docx' | 'pdf' = 'docx'): string => {
    return `${BASE_URL}/api/download/${reportId}/preview?format=${format}`;
  },

  // Get a URL for downloading the report
  getDownloadUrl: (reportId: string, format: 'docx' | 'pdf' = 'docx'): string => {
    return `${BASE_URL}/api/download/${reportId}?format=${format}`;
  },

  // Download report as blob (for direct downloads)
  downloadReport: async (reportId: string, format: 'docx' | 'pdf' = 'docx'): Promise<Blob> => {
    const response = await corsHelper.fetch(`${BASE_URL}/api/download/${reportId}?format=${format}`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to download report: ${response.statusText}`);
    }

    return response.blob();
  },

  // Download directly to device (creates download link)
  downloadToDevice: async (reportId: string, filename: string, format: 'docx' | 'pdf' = 'docx'): Promise<void> => {
    const blob = await downloadApi.downloadReport(reportId, format);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }
}; 