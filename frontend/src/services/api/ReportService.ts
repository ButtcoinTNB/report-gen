import { ApiClient, createApiClient } from './ApiClient';
import { config } from '../../../config';
import { Report, ReportPreview, AnalysisResponse } from '../../types';
import { logger } from '../../utils/logger';
import { adaptApiRequest, adaptApiResponse } from '../../utils/adapters';

/**
 * Additional information for report generation
 */
export interface AdditionalInfo {
  text: string;
}

/**
 * Response when generating a report
 */
export interface GenerateReportResponse {
  report_id: string;
  preview_url?: string;
  status: 'success' | 'error';
  message: string;
}

/**
 * Response when formatting a report
 */
export interface FormatReportResponse {
  report_id: string;
  message: string;
  status: 'success' | 'error';
}

/**
 * Response when editing a report
 */
export interface EditReportResponse {
  report_id: string;
  preview_url: string;
  status: 'success' | 'error';
  message: string;
}

// Define frontend-friendly camelCase versions of these interfaces
export interface GenerateReportResponseCamel {
  reportId: string;
  previewUrl?: string;
  status: 'success' | 'error';
  message: string;
}

export interface FormatReportResponseCamel {
  reportId: string;
  message: string;
  status: 'success' | 'error';
}

export interface EditReportResponseCamel {
  reportId: string;
  previewUrl: string;
  status: 'success' | 'error';
  message: string;
}

/**
 * API client specific to generation operations
 */
class GenerateApiClient extends ApiClient {
  /**
   * Analyze uploaded documents to extract information
   * @param reportId The report ID to analyze
   * @returns Promise with analysis response
   */
  async analyzeDocuments(reportId: string): Promise<AnalysisResponse> {
    try {
      // Convert request to snake_case for backend
      const request = adaptApiRequest({ reportId });
      
      const response = await this.post<any>('/analyze', request);
      
      // Convert response to camelCase for frontend
      return adaptApiResponse<AnalysisResponse>(response.data);
    } catch (error) {
      logger.error('Error analyzing documents:', error);
      throw error;
    }
  }

  /**
   * Generate a report based on uploaded documents and additional information
   * @param reportId The report ID to generate
   * @param additionalInfo Additional information for the report
   * @returns Promise with generation response
   */
  async generateReport(
    reportId: string, 
    additionalInfo: AdditionalInfo
  ): Promise<GenerateReportResponseCamel> {
    try {
      // Convert request to snake_case for backend
      const request = adaptApiRequest({
        reportId,
        additionalInfo: additionalInfo.text
      });
      
      const response = await this.post<GenerateReportResponse>('/generate', request);
      
      // Convert response to camelCase for frontend
      return adaptApiResponse<GenerateReportResponseCamel>(response.data);
    } catch (error) {
      logger.error('Error generating report:', error);
      throw error;
    }
  }

  /**
   * Get a preview of a report
   * @param reportId The report ID to preview
   * @returns Promise with report preview
   */
  async getReportPreview(reportId: string): Promise<ReportPreview> {
    try {
      // Use path parameter directly (no need to convert)
      const response = await this.get<any>(`/preview/${reportId}`);
      
      // Convert response to camelCase for frontend
      return adaptApiResponse<ReportPreview>(response.data);
    } catch (error) {
      logger.error('Error getting report preview:', error);
      throw error;
    }
  }

  /**
   * Get detailed information about a report
   * @param reportId The report ID
   * @returns Promise with report details
   */
  async getReport(reportId: string): Promise<Report> {
    try {
      // Use path parameter directly (no need to convert)
      const response = await this.get<any>(`/report/${reportId}`);
      
      // Convert response to camelCase for frontend
      return adaptApiResponse<Report>(response.data);
    } catch (error) {
      logger.error('Error getting report details:', error);
      throw error;
    }
  }
}

/**
 * API client specific to formatting operations
 */
class FormatApiClient extends ApiClient {
  /**
   * Format an existing report
   * @param reportId The report ID to format
   * @param style Optional style parameters
   * @returns Promise with formatting response
   */
  async formatReport(
    reportId: string, 
    style?: { [key: string]: any }
  ): Promise<FormatReportResponseCamel> {
    try {
      // Convert request to snake_case for backend
      const request = adaptApiRequest({
        reportId,
        style: style || {}
      });
      
      const response = await this.post<FormatReportResponse>('/format', request);
      
      // Convert response to camelCase for frontend
      return adaptApiResponse<FormatReportResponseCamel>(response.data);
    } catch (error) {
      logger.error('Error formatting report:', error);
      throw error;
    }
  }
}

/**
 * API client specific to editing operations
 */
class EditApiClient extends ApiClient {
  /**
   * Edit an existing report
   * @param reportId The report ID to edit
   * @param instructions Instructions for editing the report
   * @returns Promise with editing response
   */
  async editReport(
    reportId: string, 
    instructions: string
  ): Promise<EditReportResponseCamel> {
    try {
      // Convert request to snake_case for backend
      const request = adaptApiRequest({
        reportId,
        instructions
      });
      
      const response = await this.post<EditReportResponse>('/refine', request);
      
      // Convert response to camelCase for frontend
      return adaptApiResponse<EditReportResponseCamel>(response.data);
    } catch (error) {
      logger.error('Error editing report:', error);
      throw error;
    }
  }
}

/**
 * Service for report generation, analysis, formatting, and editing
 */
export class ReportService {
  private generateClient: GenerateApiClient;
  private formatClient: FormatApiClient;
  private editClient: EditApiClient;

  /**
   * Create a new Report Service
   */
  constructor() {
    // Create API clients for different endpoints
    this.generateClient = new GenerateApiClient({
      baseUrl: config.endpoints?.generate || `${config.API_URL}/api/generate`,
      defaultTimeout: 180000, // 3 minutes for generation requests
      defaultRetries: 2,
      defaultRetryDelay: 3000
    });
    
    this.formatClient = new FormatApiClient({
      baseUrl: config.endpoints?.format || `${config.API_URL}/api/format`,
      defaultTimeout: 120000, // 2 minutes for formatting requests
      defaultRetries: 2
    });
    
    this.editClient = new EditApiClient({
      baseUrl: config.endpoints?.edit || `${config.API_URL}/api/edit`,
      defaultTimeout: 180000, // 3 minutes for editing requests
      defaultRetries: 2,
      defaultRetryDelay: 3000
    });
  }

  /**
   * Analyze uploaded documents to extract information
   * @param reportId The report ID to analyze
   * @returns Promise with analysis response
   */
  async analyzeDocuments(reportId: string): Promise<AnalysisResponse> {
    return this.generateClient.analyzeDocuments(reportId);
  }

  /**
   * Generate a report based on uploaded documents and additional information
   * @param reportId The report ID to generate
   * @param additionalInfo Additional information for the report
   * @returns Promise with generation response
   */
  async generateReport(
    reportId: string, 
    additionalInfo: AdditionalInfo
  ): Promise<GenerateReportResponseCamel> {
    return this.generateClient.generateReport(reportId, additionalInfo);
  }

  /**
   * Format an existing report
   * @param reportId The report ID to format
   * @param style Optional style parameters
   * @returns Promise with formatting response
   */
  async formatReport(
    reportId: string, 
    style?: { [key: string]: any }
  ): Promise<FormatReportResponseCamel> {
    return this.formatClient.formatReport(reportId, style);
  }

  /**
   * Edit an existing report
   * @param reportId The report ID to edit
   * @param instructions Instructions for editing the report
   * @returns Promise with editing response
   */
  async editReport(
    reportId: string, 
    instructions: string
  ): Promise<EditReportResponseCamel> {
    return this.editClient.editReport(reportId, instructions);
  }

  /**
   * Get a preview of a report
   * @param reportId The report ID to preview
   * @returns Promise with report preview
   */
  async getReportPreview(reportId: string): Promise<ReportPreview> {
    return this.generateClient.getReportPreview(reportId);
  }

  /**
   * Get detailed information about a report
   * @param reportId The report ID
   * @returns Promise with report details
   */
  async getReport(reportId: string): Promise<Report> {
    return this.generateClient.getReport(reportId);
  }
}

// Export a singleton instance
export const reportService = new ReportService();

// These interfaces are already exported in their declarations above,
// so we don't need to re-export them here. 