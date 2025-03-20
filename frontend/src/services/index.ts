// Export TypeScript API Services
export * from './api';

// Export legacy API adapters for backward compatibility
export { downloadApi } from './api/download';

// Export editApi with proper adapter
import { editApi as oldEditApi } from './api/edit';
// Create a wrapped version that returns EditReportResponseCamel
export const editApi = {
  editReport: (reportId: string, instructions: string) => 
    reportService.editReport(reportId, instructions)
};

// Create adapters for the remaining APIs
import { reportService } from './api/ReportService';
import { uploadService } from './api/UploadService';
import { AdditionalInfo } from './api/ReportService';
import { Report, ReportPreview, AnalysisResponse } from '../types';
import { EditReportResponseCamel } from './api/ReportService';

// Re-export adapter interfaces that match the old API
export const generateApi = {
  analyzeDocuments: (reportId: string): Promise<AnalysisResponse> => 
    reportService.analyzeDocuments(reportId),
  
  generateReport: (reportId: string, options: { text: string }) => 
    reportService.generateReport(reportId, { text: options.text } as AdditionalInfo),
  
  // Add missing methods
  getReport: (reportId: string): Promise<Report> => 
    reportService.getReport(reportId),
    
  getReportPreview: (reportId: string): Promise<ReportPreview> => 
    reportService.getReportPreview(reportId)
};

export const uploadApi = {
  // Rename to match what components expect
  uploadFile: (files: File | File[], onProgress?: (progress: number) => void) => {
    // Handle both single file and array of files
    const fileArray = Array.isArray(files) ? files : [files];
    return uploadService.uploadFiles(fileArray, onProgress);
  },
  
  uploadFiles: (files: File[], onProgress?: (progress: number) => void) => 
    uploadService.uploadFiles(files, onProgress),
    
  uploadTemplate: (file: File, isDefault: boolean = false) => 
    uploadService.uploadTemplate(file)
};

export const formatApi = {
  formatReport: (reportId: string, options: any) => 
    reportService.formatReport(reportId, options)
}; 