import { ApiClient } from './ApiClient';
import { config } from '../../../config';

/**
 * Formats supported for report downloads
 */
export type DownloadFormat = 'docx';

/**
 * API client specific to download operations
 */
class DownloadApiClient extends ApiClient {
  /**
   * Download a report file
   * @param reportId The report ID to download
   * @param format The format to download (only 'docx' is currently supported)
   * @returns Promise that resolves with a Blob of the downloaded file
   */
  async downloadReport(reportId: string, format: DownloadFormat = 'docx'): Promise<Blob> {
    try {
      // We need to modify the request config to get a Blob response
      const response = await this.get(`/${reportId}`, {
        // Override the default response type to get a blob
      });
      
      // The response is a Blob representing the file
      return response.data as unknown as Blob;
    } catch (error) {
      console.error('Error downloading report:', error);
      throw error;
    }
  }

  /**
   * Get the URL for downloading a report
   * @param reportId The report ID to download
   * @param format The format to download (only 'docx' is currently supported)
   * @returns The URL for downloading the report
   */
  getDownloadUrl(reportId: string, format: DownloadFormat = 'docx'): string {
    if (!reportId) {
      throw new Error('Report ID is required');
    }
    
    // Return the full URL for downloading the report
    return `${this.baseUrl}/${reportId}?format=${format}`;
  }
}

/**
 * Service for downloading reports
 */
export class DownloadService {
  private downloadClient: DownloadApiClient;

  /**
   * Create a new Download Service
   */
  constructor() {
    this.downloadClient = new DownloadApiClient({
      baseUrl: config.endpoints?.download || `${config.API_URL}/api/download`,
      defaultTimeout: 300000, // 5 minutes for large downloads
      defaultRetries: 3,
      defaultRetryDelay: 2000
    });
  }

  /**
   * Download a report file as a Blob
   * @param reportId The report ID to download
   * @param format The format to download (only 'docx' is currently supported)
   * @returns Promise that resolves with a Blob of the downloaded file
   */
  async downloadReport(reportId: string, format: DownloadFormat = 'docx'): Promise<Blob> {
    return this.downloadClient.downloadReport(reportId, format);
  }

  /**
   * Get the URL for downloading a report
   * @param reportId The report ID to download
   * @param format The format to download (only 'docx' is currently supported)
   * @returns The URL for downloading the report
   */
  getDownloadUrl(reportId: string, format: DownloadFormat = 'docx'): string {
    return this.downloadClient.getDownloadUrl(reportId, format);
  }

  /**
   * Trigger a download of the report to the user's browser
   * @param reportId The report ID to download
   * @param filename The filename to use for the download
   * @param format The format to download (only 'docx' is currently supported)
   */
  downloadToDevice(reportId: string, filename: string, format: DownloadFormat = 'docx'): void {
    const downloadUrl = this.getDownloadUrl(reportId, format);
    
    // Create a temporary link element and trigger the download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || `report-${reportId}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

// Export a singleton instance
export const downloadService = new DownloadService(); 