import { adaptApiResponse } from '../utils/adapters';

export interface AnalysisDetails {
  valore: string;
  confidenza: 'ALTA' | 'MEDIA' | 'BASSA';
  richiede_verifica: boolean;
}

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
export interface ProgressUpdate {
  step: number;
  message: string;
  progress: number;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ProgressUpdateCamel {
  step: number;
  message: string;
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
export interface ReportResponse {
  content: string;
  error?: boolean;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ReportResponseCamel {
  content: string;
  error?: boolean;
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptReportResponse(response: ReportResponse): ReportResponseCamel {
  return adaptApiResponse<ReportResponseCamel>(response);
}

export interface AnalysisResponse {
  extracted_variables: Record<string, AnalysisDetails>;
  fields_needing_attention: string[];
  status: 'success' | 'error';
  message?: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface AnalysisResponseCamel {
  extractedVariables: Record<string, AnalysisDetails>;
  fieldsNeedingAttention: string[];
  status: 'success' | 'error';
  message?: string;
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
export interface ReportPreview {
  report_id: string;
  preview_url: string;
  status: 'success' | 'error';
  message?: string;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ReportPreviewCamel {
  reportId: string;
  previewUrl: string;
  status: 'success' | 'error';
  message?: string;
}

/**
 * Helper function to convert API response to frontend format
 */
export function adaptReportPreview(response: ReportPreview): ReportPreviewCamel {
  return adaptApiResponse<ReportPreviewCamel>(response);
}

export interface EditReportResponseCamel {
  reportId: string;
  previewUrl: string;
  status: 'success' | 'error';
  message: string;
} 