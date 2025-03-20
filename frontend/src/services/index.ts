// Export TypeScript API Services
export * from './api';

// Export legacy API adapters for backward compatibility
export { downloadApi } from './api/download';

// Import types
import { Report, ReportPreview, AnalysisResponse, ReportCamel, ReportPreviewCamel } from '../types';
import { 
  reportService, 
  AdditionalInfo,
  GenerateReportResponseCamel,
  FormatReportResponseCamel,
  EditReportResponseCamel
} from './api/ReportService';
import { uploadService } from './api/UploadService';
import { adaptApiResponse } from '../utils/adapters';

/**
 * Adapter for edit API to ensure type compatibility
 * Uses the reportService with proper typing
 */
export const editApi = {
  /**
   * Edit an existing report with instructions
   * @param reportId - ID of the report to edit
   * @param instructions - Text instructions for editing
   * @returns Promise with the edit response
   */
  editReport: (reportId: string, instructions: string): Promise<EditReportResponseCamel> => 
    reportService.editReport(reportId, instructions)
};

/**
 * Adapter for generate API to ensure type compatibility
 * Uses the reportService with proper typing
 */
export const generateApi = {
  /**
   * Analyze documents for a report
   * @param reportId - ID of the report to analyze
   * @returns Promise with analysis results
   */
  analyzeDocuments: (reportId: string): Promise<AnalysisResponse> => 
    reportService.analyzeDocuments(reportId),
  
  /**
   * Generate a report with additional information
   * @param reportId - ID of the report to generate
   * @param options - Additional information options
   * @returns Promise with the generation response
   */
  generateReport: (
    reportId: string, 
    options: { text: string }
  ): Promise<GenerateReportResponseCamel> => 
    reportService.generateReport(reportId, { text: options.text } as AdditionalInfo),
  
  /**
   * Get detailed report information
   * @param reportId - ID of the report to retrieve
   * @returns Promise with the report details
   */
  getReport: async (reportId: string): Promise<Report> => {
    // Get the camelCase response and convert back to snake_case for backward compatibility
    const camelResponse = await reportService.getReport(reportId);
    
    // Create a backward-compatible response with snake_case
    const response: Report = {
      report_id: camelResponse.reportId,
      template_id: camelResponse.templateId,
      title: camelResponse.title,
      content: camelResponse.content,
      file_path: camelResponse.filePath,
      preview_url: camelResponse.previewUrl,
      is_finalized: camelResponse.isFinalized,
      files_cleaned: camelResponse.filesCleaned,
      created_at: camelResponse.createdAt,
      updated_at: camelResponse.updatedAt,
      status: camelResponse.status,
      message: camelResponse.message,
      // Include legacy fields
      downloadUrl: camelResponse.downloadUrl
    };
    
    return response;
  },
    
  /**
   * Get report preview
   * @param reportId - ID of the report to preview
   * @returns Promise with the report preview
   */
  getReportPreview: async (reportId: string): Promise<ReportPreview> => {
    // Get the camelCase response and convert back to snake_case for backward compatibility
    const camelResponse = await reportService.getReportPreview(reportId);
    
    // Create a backward-compatible response with snake_case
    const response: ReportPreview = {
      report_id: camelResponse.reportId,
      preview_url: camelResponse.previewUrl,
      content: camelResponse.content,
      status: camelResponse.status,
      message: camelResponse.message,
      // Include legacy fields for backward compatibility
      reportId: camelResponse.reportId,
      previewUrl: camelResponse.previewUrl
    };
    
    return response;
  }
};

/**
 * Adapter for upload API to ensure type compatibility
 * Uses the uploadService with proper typing
 */
export const uploadApi = {
  /**
   * Upload a file or files
   * @param files - Single file or array of files to upload
   * @param onProgress - Optional progress callback
   * @returns Promise with the upload response
   */
  uploadFile: (
    files: File | File[], 
    onProgress?: (progress: number) => void
  ) => {
    // Handle both single file and array of files
    const fileArray = Array.isArray(files) ? files : [files];
    return uploadService.uploadFiles(fileArray, onProgress);
  },
  
  /**
   * Upload multiple files
   * @param files - Array of files to upload
   * @param onProgress - Optional progress callback
   * @returns Promise with the upload response
   */
  uploadFiles: (
    files: File[], 
    onProgress?: (progress: number) => void
  ) => 
    uploadService.uploadFiles(files, onProgress),
    
  /**
   * Upload a template file
   * @param file - Template file to upload
   * @param isDefault - Whether this should be the default template
   * @returns Promise with the upload response
   */
  uploadTemplate: (
    file: File, 
    isDefault: boolean = false
  ) => 
    uploadService.uploadTemplate(file)
};

/**
 * Adapter for format API to ensure type compatibility
 * Uses the reportService with proper typing
 */
export const formatApi = {
  /**
   * Format an existing report
   * @param reportId - ID of the report to format
   * @param options - Format options
   * @returns Promise with the format response
   */
  formatReport: (
    reportId: string, 
    options: Record<string, any>
  ): Promise<FormatReportResponseCamel> => 
    reportService.formatReport(reportId, options)
}; 