import { adaptApiResponse } from '../utils/adapters';

// Export all API types
export * from './api';

/**
 * Extended Report interface for application use
 * Extends from the API Report interface with additional frontend properties
 * @deprecated Use ReportCamel instead for frontend components. This interface will be removed in a future version.
 */
export interface Report {
    report_id: string;  // UUID
    template_id?: string;
    title?: string;
    content?: string;
    file_path?: string;
    preview_url?: string;
    is_finalized?: boolean;
    files_cleaned?: boolean;
    created_at?: string;
    updated_at?: string;
    status?: 'success' | 'error';
    message?: string;
    
    // Legacy fields for backward compatibility
    // These should be replaced gradually with the proper snake_case versions
    downloadUrl?: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ReportCamel {
    reportId: string;
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
 * ReportDataCamel interface extending ReportCamel for the Edit page
 * Contains all the properties needed for editing a report
 * @deprecated This interface will eventually be merged with ReportCamel
 */
export interface ReportDataCamel extends ReportCamel {
    // Currently identical to ReportCamel but separated for potential future extensions
}

/**
 * Helper function to convert API response to frontend format
 * @param response Report in snake_case format
 * @returns Report in camelCase format
 */
export function adaptReport(response: Report): ReportCamel {
    return adaptApiResponse<ReportCamel>(response);
}

/**
 * Helper function to convert API response to ReportDataCamel format
 * @param response Report in snake_case format
 * @returns ReportData in camelCase format
 */
export function adaptReportData(response: Report): ReportDataCamel {
    return adaptApiResponse<ReportDataCamel>(response);
}

/**
 * Extended ReportPreview interface for application use
 * Includes both snake_case and camelCase properties for compatibility
 * @deprecated Use ReportPreviewCamel instead for frontend components. This interface will be removed in a future version.
 */
export interface ReportPreview {
    report_id: string;
    preview_url: string;
    content?: string;
    status: 'success' | 'error';
    message?: string;
    
    // Legacy fields for backward compatibility
    // These should be replaced gradually with the proper snake_case versions
    previewUrl?: string;
    reportId?: string;
    downloadUrl?: string;
}

/**
 * Frontend-friendly version with camelCase properties only
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
 * @param response ReportPreview in snake_case format
 * @returns ReportPreview in camelCase format
 */
export function adaptReportPreview(response: ReportPreview): ReportPreviewCamel {
    return adaptApiResponse<ReportPreviewCamel>(response);
}

/**
 * Extended EditReportResponse interface
 * Extends Report with additional fields for edit operations
 * @deprecated Use EditReportResponseCamel instead for frontend components. This interface will be removed in a future version.
 */
export interface EditReportResponse extends Report {
    status: 'success' | 'error';
    message?: string;
}

/**
 * Frontend-friendly version of EditReportResponse with camelCase properties
 */
export interface EditReportResponseCamel extends ReportCamel {
    status: 'success' | 'error';
    message?: string;
}

/**
 * Helper function to convert API response to frontend format
 * @param response EditReportResponse in snake_case format
 * @returns EditReportResponse in camelCase format
 */
export function adaptEditReportResponse(response: EditReportResponse): EditReportResponseCamel {
    return adaptApiResponse<EditReportResponseCamel>(response);
}

/**
 * Response for download operations
 * @deprecated Use DownloadResponseCamel instead for frontend components. This interface will be removed in a future version.
 */
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
 * @param response DownloadResponse in snake_case format
 * @returns DownloadResponse in camelCase format
 */
export function adaptDownloadResponse(response: DownloadResponse): DownloadResponseCamel {
    return adaptApiResponse<DownloadResponseCamel>(response);
}

/**
 * Standard error format for API errors
 */
export interface ApiError {
    message: string;
    code: string;
    status: number;
}

/**
 * Import AnalysisDetails from API types to ensure consistency
 */
import { AnalysisDetails as ApiAnalysisDetails } from './api';

/**
 * Extended AnalysisResponse interface for application use
 * Aligns with the API version but includes both camelCase properties
 */
export interface AnalysisResponse {
    // Snake_case fields from API
    extracted_variables: Record<string, ApiAnalysisDetails>;
    fields_needing_attention: string[];
    status: 'success' | 'error';
    message?: string;
    
    // CamelCase fields for frontend components (derived from snake_case)
    extractedVariables: Record<string, string>;
    analysisDetails: Record<string, ComponentAnalysisDetails>;
    fieldsNeedingAttention: string[];
}

/**
 * Analysis details for components
 * This is different from the API AnalysisDetails
 */
export interface ComponentAnalysisDetails {
    confidence: number;
    source: string;
    value: string;
}

/**
 * Extended File interface for application use
 */
export interface File {
    file_id: string;
    filename: string;
    file_path: string;
    size: number;
    type: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface FileCamel {
    fileId: string;
    filename: string;
    filePath: string;
    size: number;
    type: string;
}

/**
 * Helper function to convert API response to frontend format
 * @param response File in snake_case format
 * @returns File in camelCase format
 */
export function adaptFile(response: File): FileCamel {
    return adaptApiResponse<FileCamel>(response);
}

/**
 * Extended Template interface for application use
 */
export interface Template {
    template_id: string;
    name: string;
    description?: string;
    created_at: string;
    updated_at: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface TemplateCamel {
    templateId: string;
    name: string;
    description?: string;
    createdAt: string;
    updatedAt: string;
}

/**
 * Helper function to convert API response to frontend format
 * @param response Template in snake_case format
 * @returns Template in camelCase format
 */
export function adaptTemplate(response: Template): TemplateCamel {
    return adaptApiResponse<TemplateCamel>(response);
} 