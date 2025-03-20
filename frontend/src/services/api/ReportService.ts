import { config } from '../../../config';
import { 
  Report, 
  ReportPreview, 
  AnalysisResponse,
  ReportCamel,
  ReportPreviewCamel,
} from '../../types';
import { logger } from '../../utils/logger';
import { 
  ReportPreview as ApiReportPreview, 
  AnalysisResponse as ApiAnalysisResponse 
} from '../../types/api';
import { ApiClient, createApiClient } from './ApiClient';
import { adaptApiResponse } from '../../utils/adapters';

/**
 * Additional information for report generation
 * @interface
 */
export interface AdditionalInfo {
  text: string;
}

/**
 * Response when generating a report (snake_case backend format)
 * @interface
 */
export interface GenerateReportResponse {
  report_id: string;
  preview_url?: string;
  status: 'success' | 'error';
  message: string;
}

/**
 * Response when formatting a report (snake_case backend format)
 * @interface
 */
export interface FormatReportResponse {
  report_id: string;
  message: string;
  status: 'success' | 'error';
}

/**
 * Response when editing a report (snake_case backend format)
 * @interface
 */
export interface EditReportResponse {
  report_id: string;
  preview_url: string;
  status: 'success' | 'error';
  message: string;
}

/**
 * Response when generating a report (camelCase frontend format)
 * @interface
 */
export interface GenerateReportResponseCamel {
  reportId: string;
  previewUrl?: string;
  status: 'success' | 'error';
  message: string;
}

/**
 * Response when formatting a report (camelCase frontend format)
 * @interface
 */
export interface FormatReportResponseCamel {
  reportId: string;
  message: string;
  status: 'success' | 'error';
}

/**
 * Response when editing a report (camelCase frontend format)
 * @interface
 */
export interface EditReportResponseCamel {
  reportId: string;
  previewUrl: string;
  status: 'success' | 'error';
  message: string;
}

/**
 * Interface for the report generation request
 */
export interface GenerateReportRequest {
  text: string;
}

/**
 * Report service for generating and analyzing reports
 */
export class ReportService extends ApiClient {
  /**
   * Create a new ReportService instance
   */
  constructor() {
    super({
      baseUrl: config.API_URL
    });
  }

  /**
   * Analyze documents for a report
   * @param reportId The ID of the report
   * @returns Promise with the analysis response in a format suitable for frontend components
   */
  async analyzeDocuments(reportId: string): Promise<AnalysisResponse> {
    try {
      logger.info(`Analyzing documents for report ${reportId}`);
      
      const response = await this.get<ApiAnalysisResponse>(`/documents/analyze/${reportId}`);
      
      logger.info('Analysis response:', response.data);
      
      // Convert API response to frontend format
      const adaptedResponse = adaptApiResponse<AnalysisResponse>(response.data);
      
      return adaptedResponse;
    } catch (error) {
      logger.error('Error analyzing documents:', error);
      throw error;
    }
  }

  /**
   * Generate a report based on document analysis
   * @param reportId The ID of the report
   * @param requestData Additional data for report generation
   * @returns Promise with the report preview
   */
  async generateReport(
    reportId: string, 
    requestData: GenerateReportRequest
  ): Promise<ReportPreviewCamel> {
    try {
      logger.info(`Generating report for ${reportId}`);
      
      const response = await this.post<ReportPreviewCamel>(`/reports/generate/${reportId}`, requestData);
      
      logger.info('Generation response:', response.data);
      
      return response.data;
    } catch (error) {
      logger.error('Error generating report:', error);
      throw error;
    }
  }

  /**
   * Edit a report with additional instructions
   * @param reportId The ID of the report
   * @param instructions Instructions for refining the report
   * @returns Promise with the updated report preview
   */
  async editReport(reportId: string, instructions: string): Promise<ReportPreviewCamel> {
    try {
      logger.info(`Editing report ${reportId} with instructions`);
      
      const response = await this.post<ReportPreviewCamel>(`/reports/edit/${reportId}`, { instructions });
      
      logger.info('Edit response:', response.data);
      
      return response.data;
    } catch (error) {
      logger.error('Error editing report:', error);
      throw error;
    }
  }

  /**
   * Get a report preview by ID
   * @param reportId The ID of the report
   * @returns Promise with the report preview
   */
  async getReportPreview(reportId: string): Promise<ReportPreviewCamel> {
    try {
      logger.info(`Getting preview for report ${reportId}`);
      
      const response = await this.get<ReportPreviewCamel>(`/reports/${reportId}/preview`);
      
      logger.info('Preview response:', response.data);
      
      return response.data;
    } catch (error) {
      logger.error('Error getting report preview:', error);
      throw error;
    }
  }
}

// Export a singleton instance
export const reportService = new ReportService(); 