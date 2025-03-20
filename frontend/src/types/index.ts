import { adaptApiResponse } from '../utils/adapters';

// Export all API types
export * from './api';

/**
 * Backend API interface for Report
 */
export interface Report {
    report_id: string;  // UUID
    template_id?: string;
    title?: string;
    content?: string;  // Add content field needed by components
    file_path?: string; // Add file_path needed by ReportGenerator
    preview_url?: string;
    is_finalized?: boolean;
    files_cleaned?: boolean;
    created_at?: string;
    updated_at?: string;
    status?: 'success' | 'error';
    message?: string;
    downloadUrl?: string; // Legacy field for backward compatibility
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ReportCamel {
    reportId: string;  // UUID
    templateId?: string;
    title?: string;
    content?: string;
    filePath?: string;
    previewUrl?: string;
    isFinalized?: boolean;
    filesCleaned?: boolean;
    createdAt?: string;
    updatedAt?: string;
    status?: 'success' | 'error';
    message?: string;
    downloadUrl?: string;
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptReport(response: Report): ReportCamel {
    return adaptApiResponse<ReportCamel>(response);
}

/**
 * Backend API interface for ReportPreview
 */
export interface ReportPreview {
    report_id: string;
    preview_url: string;
    content?: string;
    previewUrl?: string; // Legacy field for backward compatibility
    reportId?: string; // Legacy field for backward compatibility
    downloadUrl?: string; // Legacy field for backward compatibility
    status: 'success' | 'error';
    message?: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ReportPreviewCamel {
    reportId: string;
    previewUrl: string;
    content?: string;
    status: 'success' | 'error';
    message?: string;
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptReportPreview(response: ReportPreview): ReportPreviewCamel {
    return adaptApiResponse<ReportPreviewCamel>(response);
}

export interface EditReportResponse extends Report {
    // Additional fields specific to edit response
    status: 'success' | 'error';
    message?: string;
}

export interface DownloadResponse {
    data: {
        download_url: string;
        [key: string]: any;
    };
    status: number;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface DownloadResponseCamel {
    data: {
        downloadUrl: string;
        [key: string]: any;
    };
    status: number;
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptDownloadResponse(response: DownloadResponse): DownloadResponseCamel {
    return adaptApiResponse<DownloadResponseCamel>(response);
}

export interface ApiError {
    message: string;
    code: string;
    status: number;
}

export interface AnalysisResponse {
    extractedVariables: Record<string, string>;
    analysisDetails: Record<string, AnalysisDetails>;
    fieldsNeedingAttention: string[];
}

export interface AnalysisDetails {
    confidence: number;
    source: string;
    value: string;
}

/**
 * Backend API interface for File
 */
export interface File {
    file_id: string;  // UUID
    filename: string;
    file_path: string;
    size: number;
    type: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface FileCamel {
    fileId: string;  // UUID
    filename: string;
    filePath: string;
    size: number;
    type: string;
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptFile(response: File): FileCamel {
    return adaptApiResponse<FileCamel>(response);
}

/**
 * Backend API interface for Template
 */
export interface Template {
    template_id: string;  // UUID
    name: string;
    description?: string;
    created_at: string;
    updated_at: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface TemplateCamel {
    templateId: string;  // UUID
    name: string;
    description?: string;
    createdAt: string;
    updatedAt: string;
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptTemplate(response: Template): TemplateCamel {
    return adaptApiResponse<TemplateCamel>(response);
} 