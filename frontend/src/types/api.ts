import { adaptApiResponse } from '../utils/adapters';

/**
 * Common type conversion utilities
 * These functions help maintain type safety when converting between API response formats
 */

/**
 * Analysis details from backend in snake_case format
 */
export interface AnalysisDetails {
  valore: string;
  confidenza: 'ALTA' | 'MEDIA' | 'BASSA';
  richiede_verifica: boolean;
}

/**
 * Frontend-friendly version of AnalysisDetails with camelCase keys
 * Currently identical due to Italian field names
 */
export interface AnalysisDetailsCamel {
  valore: string;
  confidenza: 'ALTA' | 'MEDIA' | 'BASSA';
  richiede_verifica: boolean;
}

/**
 * Base response interface for consistent error handling
 */
export interface ApiResponse {
  status: 'success' | 'error';
  message: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ApiResponseCamel {
  status: 'success' | 'error';
  message: string;
}

// ========= GENERATE API TYPES =========

/**
 * Backend API interface for GenerateRequest
 */
export interface GenerateRequest {
  report_id: string;  // UUID
  document_ids: string[];  // UUIDs
  additional_info?: string;
  template_id?: string;  // UUID
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface GenerateRequestCamel {
  reportId: string;  // UUID
  documentIds: string[];  // UUIDs
  additionalInfo?: string;
  templateId?: string;  // UUID
}

/**
 * Helper function to convert frontend request to API format
 */
export function adaptGenerateRequest(request: GenerateRequestCamel): GenerateRequest {
  return adaptApiResponse<GenerateRequest>(request);
}

/**
 * Backend API interface for RefineRequest
 */
export interface RefineRequest {
  report_id: string;  // UUID
  instructions: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface RefineRequestCamel {
  reportId: string;  // UUID
  instructions: string;
}

/**
 * Helper function to convert frontend request to API format
 */
export function adaptRefineRequest(request: RefineRequestCamel): RefineRequest {
  return adaptApiResponse<RefineRequest>(request);
}

/**
 * Backend API interface for ProgressUpdate
 */
export interface ProgressUpdate extends ApiResponse {
  step: number;
  progress: number;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ProgressUpdateCamel extends ApiResponseCamel {
  step: number;
  progress: number;
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptProgressUpdate(response: ProgressUpdate): ProgressUpdateCamel {
  return adaptApiResponse<ProgressUpdateCamel>(response);
}

/**
 * Backend API interface for ReportResponse
 */
export interface ReportResponse extends ApiResponse {
  content: string;
  error?: boolean;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ReportResponseCamel extends ApiResponseCamel {
  content: string;
  error?: boolean;
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptReportResponse(response: ReportResponse): ReportResponseCamel {
  return adaptApiResponse<ReportResponseCamel>(response);
}

/**
 * Backend API interface for AnalysisResponse
 */
export interface AnalysisResponse extends ApiResponse {
  extracted_variables: Record<string, AnalysisDetails>;
  fields_needing_attention: string[];
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface AnalysisResponseCamel extends ApiResponseCamel {
  extractedVariables: Record<string, AnalysisDetails>;
  fieldsNeedingAttention: string[];
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptAnalysisResponse(response: AnalysisResponse): AnalysisResponseCamel {
  return adaptApiResponse<AnalysisResponseCamel>(response);
}

/**
 * Backend API interface for ReportPreview
 */
export interface ReportPreview extends ApiResponse {
  report_id: string;
  preview_url: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ReportPreviewCamel extends ApiResponseCamel {
  reportId: string;
  previewUrl: string;
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptReportPreview(response: ReportPreview): ReportPreviewCamel {
  return adaptApiResponse<ReportPreviewCamel>(response);
}

/**
 * Backend API interface for EditReportResponse
 */
export interface EditReportResponse extends ReportPreview {
  // EditReportResponse extends ReportPreview with the same fields
}

/**
 * Frontend-friendly version with camelCase properties
 */
export type EditReportResponseCamel = ReportPreviewCamel;

/**
 * Helper function to convert API response to frontend format
 */
export function adaptEditReportResponse(response: EditReportResponse): EditReportResponseCamel {
  return adaptApiResponse<EditReportResponseCamel>(response);
} 