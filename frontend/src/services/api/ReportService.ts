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
import { ApiClient, createApiClient, ApiRequestOptions } from './ApiClient';
import { adaptApiResponse, adaptApiRequest } from '../../utils/adapters';

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
 * Agent loop request interface
 */
export interface AgentLoopRequest {
  reportId: string;
  additionalInfo: string;
}

/**
 * Agent loop response interface with feedback
 */
export interface AgentLoopResponse {
  draft: string;
  feedback: {
    score: number;
    suggestions: string[];
  };
  iterations: number;
  docxUrl?: string;
  taskId?: string;
}

/**
 * Task status response interface
 */
export interface TaskStatusResponse {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number | null;
  result?: any;
  error?: string;
  estimatedCompletionTime?: number;
}

/**
 * Report service for generating and analyzing reports
 */
export class ReportService extends ApiClient {
  // Default timeout for agent loop initialization (15 seconds)
  private readonly DEFAULT_AGENT_INIT_TIMEOUT = 15000;
  
  // Maximum retries for agent loop initialization
  private readonly MAX_AGENT_INIT_RETRIES = 3;
  
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
   * Initialize the agent loop for report generation
   * @param request Agent loop initialization request
   * @param onProgress Optional callback for progress updates
   * @returns Promise with the agent loop response
   */
  async initializeAgentLoop(
    request: AgentLoopRequest,
    onProgress?: (progress: number, status: string) => void
  ): Promise<AgentLoopResponse> {
    // Convert camelCase to snake_case for the backend
    const apiRequest = adaptApiRequest({
      report_id: request.reportId,
      additional_info: request.additionalInfo
    });
    
    // Set up retry logic
    let retryCount = 0;
    let lastError: Error | null = null;
    
    while (retryCount <= this.MAX_AGENT_INIT_RETRIES) {
      try {
        if (retryCount > 0) {
          logger.info(`Retrying agent loop initialization (${retryCount}/${this.MAX_AGENT_INIT_RETRIES})`);
          // Wait with exponential backoff before retrying
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
          
          if (onProgress) {
            onProgress(0, `Ritentativo di inizializzazione (${retryCount}/${this.MAX_AGENT_INIT_RETRIES})...`);
          }
        }
        
        // Set up request options with timeout
        const options: ApiRequestOptions = {
          timeout: this.DEFAULT_AGENT_INIT_TIMEOUT,
          retryOptions: {
            maxRetries: 0, // We're handling retries manually
          }
        };
        
        // Update progress to indicate request is being sent
        if (onProgress) {
          onProgress(10, 'Inizializzazione del processo di generazione...');
        }
        
        logger.info('Initializing agent loop with request:', request);
        const response = await this.post<any>('/agent-loop/generate-report', apiRequest, options);
        
        // Validate the response
        if (!response.data) {
          throw new Error('Invalid response: No data received');
        }
        
        // If we received a task ID instead of the full response, we need to poll for status
        if (response.data.task_id) {
          // Update progress to indicate polling has started
          if (onProgress) {
            onProgress(20, 'Processo avviato, monitoraggio in corso...');
          }
          
          return this.pollTaskStatus(response.data.task_id, onProgress);
        }
        
        // Convert snake_case to camelCase for the frontend
        const adaptedResponse = adaptApiResponse<AgentLoopResponse>(response.data);
        
        // If response doesn't have required fields, throw an error
        if (!adaptedResponse.draft) {
          throw new Error('Invalid response format: missing draft content');
        }
        
        // Update progress to indicate success
        if (onProgress) {
          onProgress(100, 'Inizializzazione completata con successo');
        }
        
        return adaptedResponse;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        logger.error(`Agent loop initialization error (attempt ${retryCount + 1}):`, error);
        retryCount++;
        
        // If we've reached the max retries, throw the last error
        if (retryCount > this.MAX_AGENT_INIT_RETRIES) {
          throw lastError;
        }
      }
    }
    
    // This should never be reached due to the throw above, but TypeScript requires a return
    throw lastError || new Error('Failed to initialize agent loop after maximum retries');
  }
  
  /**
   * Poll for task status until completion or failure
   * @param taskId The task ID to poll
   * @param onProgress Optional callback for progress updates
   * @returns Promise with the agent loop response
   */
  private async pollTaskStatus(
    taskId: string,
    onProgress?: (progress: number, status: string) => void
  ): Promise<AgentLoopResponse> {
    const maxPolls = 60; // Maximum number of polling attempts (10 minutes at 10s intervals)
    let pollCount = 0;
    
    while (pollCount < maxPolls) {
      try {
        // Wait before polling to avoid overloading the server
        await new Promise(resolve => setTimeout(resolve, 10000));
        
        const response = await this.get<TaskStatusResponse>(`/agent-loop/task-status/${taskId}`);
        const status = response.data;
        
        // Update progress based on task status
        if (status.progress && onProgress) {
          // Map server progress (0-1) to our scale (20-90)
          const scaledProgress = 20 + status.progress * 70;
          onProgress(scaledProgress, `Generazione del report in corso (${Math.round(status.progress * 100)}%)...`);
        }
        
        // Check if the task is complete
        if (status.status === 'completed' && status.result) {
          // Convert snake_case to camelCase for the frontend
          const adaptedResult = adaptApiResponse<AgentLoopResponse>(status.result);
          
          // Update progress to indicate success
          if (onProgress) {
            onProgress(100, 'Generazione completata con successo');
          }
          
          return {
            ...adaptedResult,
            taskId
          };
        }
        
        // Check if the task failed
        if (status.status === 'failed') {
          throw new Error(status.error || 'Task failed with unknown error');
        }
        
        pollCount++;
      } catch (error) {
        logger.error('Error polling task status:', error);
        throw error;
      }
    }
    
    throw new Error('Timeout: Task took too long to complete');
  }

  /**
   * Cancel an ongoing agent loop task
   * @param taskId The task ID to cancel
   * @returns Promise indicating success or failure
   */
  async cancelAgentLoop(taskId: string): Promise<{ status: string; message: string }> {
    try {
      logger.info(`Cancelling agent loop task ${taskId}`);
      
      const response = await this.post<{ status: string; message: string }>(`/agent-loop/cancel-task/${taskId}`, {});
      
      return response.data;
    } catch (error) {
      logger.error('Error cancelling agent loop task:', error);
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