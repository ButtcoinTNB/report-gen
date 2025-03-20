/**
 * adapters.ts
 * 
 * Adapter Pattern Implementation for Insurance Report Generator
 * 
 * This module implements the Adapter Pattern to handle the conversion between
 * snake_case (used by the Python backend API) and camelCase (used by the TypeScript frontend).
 * 
 * ## Architecture Overview
 * 
 * Our application has a clear separation between backend and frontend:
 * - Backend (Python): Uses snake_case for all property names (e.g., 'report_id', 'file_path')
 * - Frontend (TypeScript): Uses camelCase per JavaScript/TypeScript conventions (e.g., 'reportId', 'filePath')
 * 
 * ## Design Principles
 * 
 * 1. **One-way Data Flow**:
 *    - Backend data → adaptApiResponse → Frontend components (snake_case → camelCase)
 *    - Frontend data → adaptApiRequest → Backend API (camelCase → snake_case)
 * 
 * 2. **Type Safety**:
 *    - We maintain parallel interface definitions:
 *      - Snake case (e.g., `ReportPreview`) for API communication
 *      - Camel case (e.g., `ReportPreviewCamel`) for frontend components
 *    - The `CamelCase<T>` utility type automates generating camelCase equivalents
 * 
 * 3. **Transition Strategy**:
 *    - Hybrid objects with both snake_case and camelCase fields support gradual migration
 *    - The snake_case analysis tool tracks migration progress
 *    - ESLint rules detect snake_case usage in frontend code
 * 
 * ## Usage Guidelines
 * 
 * 1. **API Services**:
 *    - Use adaptApiRequest() when sending data to the backend
 *    - Use adaptApiResponse() when receiving data from the backend
 *    - It's normal for API services to reference snake_case properties
 * 
 * 2. **Components**:
 *    - Always use camelCase properties in React components
 *    - Import and use the *Camel interfaces (e.g., ReportPreviewCamel)
 *    - Never directly access snake_case properties in component code
 * 
 * 3. **Types**:
 *    - Create new interfaces with generate:api-interfaces script
 *    - Use the CamelCase<T> utility type for dynamic conversion
 *    - Place API-specific types in api.ts, frontend types in index.ts
 * 
 * ## Example Workflow
 * 
 * ```typescript
 * // 1. API layer: Fetch data from backend (snake_case)
 * const apiResponse = await axios.get('/api/report/123');
 * 
 * // 2. Adapt response to frontend format (camelCase)
 * const reportData = adaptApiResponse<ReportPreviewCamel>(apiResponse.data);
 * 
 * // 3. Use camelCase properties in component
 * const ReportComponent = () => {
 *   return <div>{reportData.reportId} - {reportData.previewUrl}</div>;
 * };
 * 
 * // 4. Send data back to API (convert to snake_case)
 * const updateData = { reportId: '123', status: 'complete' };
 * await axios.post('/api/report', adaptApiRequest(updateData));
 * ```
 * 
 * @see {@link MIGRATION.md} for the complete migration guide
 */

import { logger } from './logger';
import { 
  ReportPreview, 
  ReportPreviewCamel, 
  AnalysisResponse,
  ComponentAnalysisDetails
} from '../types';
import { AnalysisDetails, AnalysisResponse as ApiAnalysisResponse } from '../types/api';

/**
 * Convert a string from snake_case to camelCase
 * 
 * This function transforms property names from backend format to frontend format.
 * It's used both directly and as part of the object conversion utilities.
 * 
 * @example
 * snakeToCamel('hello_world') // returns 'helloWorld'
 * snakeToCamel('report_id') // returns 'reportId'
 * snakeToCamel('preview_url') // returns 'previewUrl'
 * 
 * @param str The snake_case string to convert
 * @returns The converted camelCase string
 */
export function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Convert a string from camelCase to snake_case
 * 
 * This function transforms property names from frontend format to backend format.
 * It's used both directly and as part of the object conversion utilities.
 * 
 * @example
 * camelToSnake('helloWorld') // returns 'hello_world'
 * camelToSnake('reportId') // returns 'report_id'
 * camelToSnake('previewUrl') // returns 'preview_url'
 * 
 * @param str The camelCase string to convert
 * @returns The converted snake_case string
 */
export function camelToSnake(str: string): string {
  return str.replace(/([A-Z])/g, (_, letter) => `_${letter.toLowerCase()}`);
}

/**
 * Transform an object's keys from snake_case to camelCase
 * 
 * This utility recursively processes an object and all its nested objects and arrays,
 * converting all property keys from snake_case to camelCase format.
 * 
 * @example
 * const apiResponse = { report_id: '123', user_data: { first_name: 'John' } };
 * const frontendData = snakeToCamelObject(apiResponse);
 * // Result: { reportId: '123', userData: { firstName: 'John' } }
 * 
 * @param obj The snake_case object to transform
 * @returns A new object with camelCase keys (original object is not modified)
 */
export function snakeToCamelObject<T = any>(obj: Record<string, any>): T {
  if (obj === null || obj === undefined || typeof obj !== 'object') {
    return obj as unknown as T;
  }

  if (Array.isArray(obj)) {
    return obj.map(item => snakeToCamelObject(item)) as unknown as T;
  }

  return Object.keys(obj).reduce((result, key) => {
    const camelKey = snakeToCamel(key);
    const value = obj[key];
    
    // Recursively convert nested objects
    if (value !== null && typeof value === 'object') {
      result[camelKey] = snakeToCamelObject(value);
    } else {
      result[camelKey] = value;
    }
    
    return result;
  }, {} as Record<string, any>) as T;
}

/**
 * Transform an object's keys from camelCase to snake_case
 * 
 * This utility recursively processes an object and all its nested objects and arrays,
 * converting all property keys from camelCase to snake_case format.
 * 
 * @example
 * const frontendData = { reportId: '123', userData: { firstName: 'John' } };
 * const apiRequest = camelToSnakeObject(frontendData);
 * // Result: { report_id: '123', user_data: { first_name: 'John' } }
 * 
 * @param obj The camelCase object to transform
 * @returns A new object with snake_case keys (original object is not modified)
 */
export function camelToSnakeObject<T = any>(obj: Record<string, any>): T {
  if (obj === null || obj === undefined || typeof obj !== 'object') {
    return obj as unknown as T;
  }

  if (Array.isArray(obj)) {
    return obj.map(item => camelToSnakeObject(item)) as unknown as T;
  }

  return Object.keys(obj).reduce((result, key) => {
    const snakeKey = camelToSnake(key);
    const value = obj[key];
    
    // Recursively convert nested objects
    if (value !== null && typeof value === 'object') {
      result[snakeKey] = camelToSnakeObject(value);
    } else {
      result[snakeKey] = value;
    }
    
    return result;
  }, {} as Record<string, any>) as T;
}

/**
 * API adapter to convert backend responses (snake_case) to frontend format (camelCase)
 * 
 * This is the primary function for processing API responses. Use this in API service
 * methods when receiving data from the backend to ensure consistent frontend formatting.
 * 
 * @example
 * // In an API service method:
 * async getReport(id: string): Promise<ReportPreviewCamel> {
 *   const response = await this.get(`/reports/${id}`);
 *   return adaptApiResponse<ReportPreviewCamel>(response.data);
 * }
 * 
 * @param response The API response from the backend
 * @returns A transformed response with camelCase keys
 */
export function adaptApiResponse<T = any>(response: any): T {
  try {
    return snakeToCamelObject<T>(response);
  } catch (error) {
    logger.error('Error adapting API response:', error);
    // Return original response if conversion fails
    return response as unknown as T;
  }
}

/**
 * API adapter to convert frontend requests (camelCase) to backend format (snake_case)
 * 
 * This is the primary function for preparing data to send to the API. Use this in API
 * service methods when sending data to the backend to ensure compatibility.
 * 
 * @example
 * // In an API service method:
 * async updateReport(reportId: string, data: ReportUpdateCamel): Promise<void> {
 *   const requestData = adaptApiRequest(data);
 *   await this.post(`/reports/${reportId}`, requestData);
 * }
 * 
 * @param request The request object from the frontend
 * @returns A transformed request with snake_case keys
 */
export function adaptApiRequest<T = any>(request: any): T {
  try {
    return camelToSnakeObject<T>(request);
  } catch (error) {
    logger.error('Error adapting API request:', error);
    // Return original request if conversion fails
    return request as unknown as T;
  }
}

/**
 * Creates a complete AnalysisResponse object from API response
 * Converts from API format (snake_case) to a hybrid format with both
 * snake_case fields (for API compatibility) and camelCase fields (for components)
 * 
 * @param apiResponse The raw API response with snake_case properties
 * @returns A hybrid AnalysisResponse with both snake_case and camelCase properties
 */
export function createAnalysisResponse(apiResponse: ApiAnalysisResponse): AnalysisResponse {
  try {
    // First create the camelCase fields via the general adapter
    const camelResponse = adaptApiResponse<Partial<AnalysisResponse>>(apiResponse);
    
    // Then build the component-specific analysis details
    const analysisDetails: Record<string, ComponentAnalysisDetails> = {};
    
    // Convert the API analysis details to component-friendly format
    // Note: The API uses Italian field names (valore, confidenza, richiede_verifica)
    Object.entries(apiResponse.extracted_variables || {}).forEach(([key, details]) => {
      // Map the Italian field names to our component's English field names
      analysisDetails[key] = {
        confidence: getConfidenceLevel(details.confidenza), // Convert Italian confidence level to numeric
        source: details.richiede_verifica ? 'needs_verification' : 'automatic',
        value: details.valore
      };
    });
    
    // Create a simplified record of extracted variables (just key -> value mapping)
    const extractedVariables: Record<string, string> = {};
    Object.entries(apiResponse.extracted_variables || {}).forEach(([key, details]) => {
      extractedVariables[key] = details.valore; // Use the Italian field name 'valore'
    });
    
    // Return the complete hybrid response
    return {
      // Original snake_case properties from API
      extracted_variables: apiResponse.extracted_variables || {},
      fields_needing_attention: apiResponse.fields_needing_attention || [],
      status: apiResponse.status,
      message: apiResponse.message,
      
      // Processed camelCase properties for components
      extractedVariables,
      analysisDetails,
      fieldsNeedingAttention: apiResponse.fields_needing_attention || []
    };
  } catch (error) {
    logger.error('Error creating analysis response:', error);
    // Return a minimal valid object if conversion fails
    return {
      extracted_variables: {},
      fields_needing_attention: [],
      status: 'error',
      message: 'Failed to process analysis response',
      extractedVariables: {},
      analysisDetails: {},
      fieldsNeedingAttention: []
    };
  }
}

/**
 * Helper function to convert Italian confidence levels to numeric values
 * @param confidenza The Italian confidence level
 * @returns A numeric confidence value between 0 and 1
 */
function getConfidenceLevel(confidenza?: 'ALTA' | 'MEDIA' | 'BASSA'): number {
  switch (confidenza) {
    case 'ALTA':
      return 0.9; // High confidence
    case 'MEDIA':
      return 0.6; // Medium confidence 
    case 'BASSA':
      return 0.3; // Low confidence
    default:
      return 0.5; // Default to medium confidence if not specified
  }
}

/**
 * Utility to create a hybrid Report Preview with both camelCase and snake_case fields
 * This is useful for components that need backwards compatibility
 * @param camelResponse The camelCase response (from the API adapter)
 * @returns A combined response with both formats for compatibility
 */
export function createHybridReportPreview(camelResponse: ReportPreviewCamel): ReportPreview {
  // Create a backward-compatible response with snake_case and legacy camelCase
  return {
    // Base snake_case fields
    report_id: camelResponse.reportId,
    preview_url: camelResponse.previewUrl,
    content: camelResponse.content,
    status: camelResponse.status,
    message: camelResponse.message,

    // Legacy camelCase fields for backward compatibility
    reportId: camelResponse.reportId,
    previewUrl: camelResponse.previewUrl
  };
}

/**
 * Creates a new set of interfaces that use camelCase from the snake_case API responses
 * This is useful for creating client-side interfaces that match TypeScript conventions
 * 
 * Example usage:
 * ```
 * // Backend API interface (snake_case)
 * interface ApiResponse {
 *   report_id: string;
 *   preview_url: string;
 * }
 * 
 * // Frontend interface (camelCase)
 * type ClientResponse = CamelCase<ApiResponse>;
 * // Equivalent to:
 * // interface ClientResponse {
 * //   reportId: string;
 * //   previewUrl: string;
 * // }
 * ```
 */
export type CamelCase<T> = {
  [K in keyof T as K extends string ? typeof snakeToCamel extends (str: string) => infer R
    ? K extends string
      ? R extends string
        ? R
        : never
      : never
    : never : K]: T[K] extends Record<string, any>
    ? CamelCase<T[K]>
    : T[K] extends Array<Record<string, any>>
      ? CamelCase<T[K][number]>[]
      : T[K];
}; 