import { config } from '../../../config';
import { apiConfig } from '../../config/api.config';
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
import { store } from '../../store';
import { beginTransaction, completeTransaction } from '../../store/reportSlice';
import { v4 as uuidv4 } from 'uuid';
import { ApiService } from './ApiService';
import apiClient from '../api';

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
  message?: string;
}

/**
 * Progress update callback type
 */
interface ProgressCallback {
  (progress: number, status: string, transactionId?: string): void;
}

/**
 * Add this interface for report versions
 * @interface
 */
export interface ReportVersion {
  version_id: string;
  version_number: number;
  created_at: string;
  created_by: string;
  created_by_ai: boolean;
  changes_description: string;
  content: string;
}

/**
 * Define the report interface
 * @interface
 */
export interface Report {
  report_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  current_version: number;
  status: 'draft' | 'review' | 'final';
  content: string;
  metadata: Record<string, any>;
}

/**
 * Define the version history response
 * @interface
 */
export interface VersionHistoryResponse {
  report_id: string;
  current_version: number;
  versions: ReportVersion[];
}

/**
 * Report service for generating and analyzing reports
 */
export class ReportService extends ApiService {
  // Use configurable timeout values
  private readonly DEFAULT_AGENT_INIT_TIMEOUT = apiConfig.timeouts.agentInit;
  
  // Use configurable retry values
  private readonly MAX_AGENT_INIT_RETRIES = apiConfig.retry.maxRetries;
  
  // WebSocket connections for task status
  private webSocketConnections: Map<string, WebSocket> = new Map();
  
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
          const backoffTime = Math.pow(apiConfig.retry.backoffFactor, retryCount) * apiConfig.retry.initialBackoff;
          await new Promise(resolve => setTimeout(resolve, backoffTime));
          
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
        const response = await this.post<any>(apiConfig.endpoints.agentLoop, apiRequest, options);
        
        // Validate the response
        if (!response.data) {
          throw new Error('Invalid response: No data received');
        }
        
        // If we received a task ID instead of the full response, we need to track its status
        if (response.data.task_id) {
          // Update progress to indicate task is being tracked
          if (onProgress) {
            onProgress(20, 'Processo avviato, monitoraggio in corso...');
          }
          
          // Determine whether to use WebSockets or polling
          if (apiConfig.webSocket.enabled && this.isWebSocketSupported()) {
            return this.trackTaskStatusWithWebSocket(response.data.task_id, onProgress);
          } else {
            return this.pollTaskStatus(response.data.task_id, onProgress);
          }
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
   * Check if WebSockets are supported in the current environment
   * @returns Boolean indicating whether WebSockets are supported
   */
  private isWebSocketSupported(): boolean {
    return typeof WebSocket !== 'undefined';
  }
  
  /**
   * Cancel an ongoing agent loop task
   * @param taskId The task ID to cancel
   * @param userId Optional user ID for security validation
   * @returns Promise indicating success or failure
   */
  async cancelAgentLoop(
    taskId: string, 
    userId?: string
  ): Promise<{ status: string; message: string }> {
    try {
      // Start a cancellation transaction for state management
      const transactionAction = beginTransaction({
        operation: 'cancel',
        taskId
      });
      
      // The transaction ID is returned in the reducer function, not directly in the action
      // We'll get it from the state after dispatch
      store.dispatch(transactionAction);
      
      // Get the transaction ID from the state after dispatching
      const state = store.getState();
      const transactionId = state.report.agentLoop.transactionId;
      
      logger.info(`Cancelling agent loop task ${taskId} (Transaction: ${transactionId})`);
      
      // Clean up any WebSocket connection for this task
      this.closeWebSocketConnection(taskId);
      
      // Set up request with timeout
      const options: ApiRequestOptions = {
        timeout: apiConfig.timeouts.cancelOperation,
      };
      
      // Include userId if provided for security validation
      const payload = userId ? { userId } : {};
      
      const response = await this.post<{ status: string; message: string }>(
        `${apiConfig.endpoints.cancelTask}/${taskId}`,
        payload,
        options
      );
      
      // Complete the transaction successfully
      store.dispatch(completeTransaction({
        transactionId: transactionId!,
        success: true
      }));
      
      return response.data;
    } catch (error) {
      const state = store.getState();
      const transactionId = state.report.agentLoop.transactionId;
      logger.error(`Error cancelling agent loop task: ${error} (Transaction: ${transactionId})`);
      
      // Complete transaction with failure status
      if (transactionId) {
        store.dispatch(completeTransaction({
          transactionId,
          success: false
        }));
      }
      
      // For network errors, send a cancellation notification on reconnect
      if (this.isNetworkError(error)) {
        // Set a flag to try cancellation again when network is available
        this.scheduleRetryCancellation(taskId, userId);
      }
      
      throw error;
    }
  }
  
  /**
   * Schedule a retry of cancellation when network becomes available
   * @param taskId The task ID to cancel
   * @param userId Optional user ID for security validation
   */
  private scheduleRetryCancellation(taskId: string, userId?: string): void {
    // Use navigator.onLine if available to detect when network is restored
    if (typeof window !== 'undefined' && 'navigator' in window) {
      const handler = () => {
        if (navigator.onLine) {
          // Network is back, try cancellation again
          this.cancelAgentLoop(taskId, userId)
            .catch(e => logger.error('Retry cancellation failed:', e));
          
          // Remove event listeners
          window.removeEventListener('online', handler);
        }
      };
      
      // Listen for network restoration
      window.addEventListener('online', handler);
      
      // Set a timeout to stop listening after a reasonable time
      setTimeout(() => {
        window.removeEventListener('online', handler);
      }, 5 * 60 * 1000); // 5 minutes
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

  /**
   * Handle WebSocket reconnection logic
   */
  private handleWebSocketReconnect(
    taskId: string,
    reconnectAttempts: number,
    onProgress?: ProgressCallback,
    resolve?: (value: AgentLoopResponse | PromiseLike<AgentLoopResponse>) => void,
    reject?: (reason?: any) => void
  ): void {
    reconnectAttempts++;
    
    // Start a reconnection transaction for state management
    const transactionAction = beginTransaction({
      operation: 'reconnect',
      taskId,
      retryCount: reconnectAttempts
    });
    
    // Dispatch the action
    store.dispatch(transactionAction);
    
    // Get the transaction ID from the state after dispatching
    const state = store.getState();
    const transactionId = state.report.agentLoop.transactionId;
    
    if (reconnectAttempts <= apiConfig.webSocket.maxReconnectAttempts) {
      logger.info(`Attempting WebSocket reconnect ${reconnectAttempts}/${apiConfig.webSocket.maxReconnectAttempts} for task ${taskId} (Transaction: ${transactionId})`);
      
      if (onProgress) {
        onProgress(
          20, // Keep the same progress level during reconnection attempts
          `Riconnessione in corso (${reconnectAttempts}/${apiConfig.webSocket.maxReconnectAttempts})...`,
          transactionId || undefined
        );
      }
      
      // Attempt to reconnect after the specified interval
      setTimeout(() => {
        try {
          this.trackTaskStatusWithWebSocket(taskId, onProgress, transactionId)
            .then((result) => {
              // Complete the transaction successfully
              store.dispatch(completeTransaction({
                transactionId,
                success: true
              }));
              
              if (resolve) resolve(result);
            })
            .catch((error) => {
              // Complete transaction with failure status
              store.dispatch(completeTransaction({
                transactionId,
                success: false
              }));
              
              if (reject) reject(error);
            });
        } catch (error) {
          // Complete transaction with failure status
          store.dispatch(completeTransaction({
            transactionId,
            success: false
          }));
          
          if (reject) reject(error);
        }
      }, apiConfig.webSocket.reconnectInterval);
    } else if (apiConfig.webSocket.fallbackToPolling) {
      // Fall back to polling if configured
      logger.info(`Falling back to polling after ${reconnectAttempts} failed reconnection attempts for task ${taskId} (Transaction: ${transactionId})`);
      
      if (onProgress) {
        onProgress(20, 'Passaggio a polling dopo tentativi di riconnessione falliti...', transactionId);
      }
      
      try {
        this.pollTaskStatus(taskId, onProgress, transactionId)
          .then((result) => {
            // Complete the transaction successfully
            store.dispatch(completeTransaction({
              transactionId,
              success: true
            }));
            
            if (resolve) resolve(result);
          })
          .catch((error) => {
            // Complete transaction with failure status
            store.dispatch(completeTransaction({
              transactionId,
              success: false
            }));
            
            if (reject) reject(error);
          });
      } catch (error) {
        // Complete transaction with failure status
        store.dispatch(completeTransaction({
          transactionId,
          success: false
        }));
        
        if (reject) reject(error);
      }
    } else {
      // No more reconnection attempts and no fallback, so reject
      // Complete transaction with failure status
      store.dispatch(completeTransaction({
        transactionId,
        success: false
      }));
      
      if (reject) reject(new Error(`WebSocket connection failed after ${reconnectAttempts} attempts`));
    }
  }
  
  /**
   * Track task status with WebSocket for real-time updates
   * @param taskId The task ID to track
   * @param onProgress Optional callback for progress updates
   * @param transactionId Optional transaction ID for state management
   * @returns Promise with the agent loop response
   */
  private trackTaskStatusWithWebSocket(
    taskId: string,
    onProgress?: ProgressCallback,
    transactionId?: string
  ): Promise<AgentLoopResponse> {
    return new Promise((resolve, reject) => {
      // Build the WebSocket URL using the same origin as the API
      const apiUrl = new URL(config.API_URL);
      const protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${apiUrl.host}${apiConfig.endpoints.taskEvents}/${taskId}`;
      
      logger.info(`Connecting to WebSocket for task ${taskId}`);
      
      let reconnectAttempts = 0;
      let connectionClosed = false;
      
      // Function to establish WebSocket connection
      const connectWebSocket = () => {
        // Close existing connection if any
        this.closeWebSocketConnection(taskId);
        
        const socket = new WebSocket(wsUrl);
        this.webSocketConnections.set(taskId, socket);
        
        // Set a connection timeout
        const connectionTimeout = setTimeout(() => {
          if (socket.readyState !== WebSocket.OPEN) {
            logger.warn(`WebSocket connection timeout for task ${taskId}`);
            socket.close();
            
            // Fall back to polling if configured
            if (apiConfig.webSocket.fallbackToPolling) {
              logger.info(`Falling back to polling for task ${taskId}`);
              this.pollTaskStatus(taskId, onProgress, transactionId)
                .then(resolve)
                .catch(reject);
            } else {
              reject(new Error('WebSocket connection timeout'));
            }
          }
        }, apiConfig.timeouts.agentInit);
        
        socket.onopen = () => {
          logger.info(`WebSocket connection established for task ${taskId}`);
          clearTimeout(connectionTimeout);
        };
        
        socket.onmessage = (event) => {
          try {
            // Skip heartbeat messages
            if (event.data.startsWith(':')) return;
            
            // Parse the data
            const dataStr = event.data.replace('data: ', '');
            const data = JSON.parse(dataStr);
            
            logger.debug(`WebSocket message for task ${taskId}:`, data);
            
            // Update progress
            if (data.progress !== undefined && onProgress) {
              // Map server progress (0-1) to our scale (20-90)
              const min = apiConfig.progressScaling.agentProcessing.min;
              const max = apiConfig.progressScaling.agentProcessing.max;
              const scaledProgress = min + data.progress * (max - min);
              
              onProgress(
                scaledProgress, 
                data.message || `Generazione del report in corso (${Math.round(data.progress * 100)}%)...`,
                transactionId
              );
            }
            
            // Check if the task is complete
            if (data.status === 'completed' && data.result) {
              // Convert snake_case to camelCase for the frontend
              const adaptedResult = adaptApiResponse<AgentLoopResponse>(data.result);
              
              // Update progress to indicate success
              if (onProgress) {
                onProgress(100, 'Generazione completata con successo', transactionId);
              }
              
              // Clean up WebSocket connection
              connectionClosed = true;
              this.closeWebSocketConnection(taskId);
              
              resolve({
                ...adaptedResult,
                taskId
              });
            }
            
            // Check if the task failed
            if (data.status === 'failed') {
              connectionClosed = true;
              this.closeWebSocketConnection(taskId);
              reject(new Error(data.error || 'Task failed with unknown error'));
            }
            
            // Check if the task expired or was removed
            if (data.status === 'expired') {
              connectionClosed = true;
              this.closeWebSocketConnection(taskId);
              reject(new Error('Task expired or was removed from the server'));
            }
          } catch (error) {
            logger.error('Error processing WebSocket message:', error);
          }
        };
        
        socket.onerror = (error) => {
          logger.error(`WebSocket error for task ${taskId}:`, error);
          
          // Only attempt reconnect if the connection isn't intentionally closed
          if (!connectionClosed) {
            this.handleWebSocketReconnect(taskId, reconnectAttempts, onProgress, resolve, reject);
          }
        };
        
        socket.onclose = (event) => {
          if (!connectionClosed) {
            logger.warn(`WebSocket connection closed for task ${taskId}: ${event.code} ${event.reason}`);
            this.handleWebSocketReconnect(taskId, reconnectAttempts, onProgress, resolve, reject);
          }
        };
      };
      
      // Start the WebSocket connection
      connectWebSocket();
    });
  }
  
  /**
   * Close a WebSocket connection and clean up
   * @param taskId The task ID associated with the connection
   */
  private closeWebSocketConnection(taskId: string): void {
    const socket = this.webSocketConnections.get(taskId);
    
    if (socket) {
      // Only close if it's not already closed
      if (socket.readyState !== WebSocket.CLOSED && socket.readyState !== WebSocket.CLOSING) {
        socket.close();
      }
      
      this.webSocketConnections.delete(taskId);
    }
  }
  
  /**
   * Poll for task status until completion or failure (fallback method)
   * @param taskId The task ID to poll
   * @param onProgress Optional callback for progress updates
   * @param transactionId Optional transaction ID for state management
   * @returns Promise with the agent loop response
   */
  private async pollTaskStatus(
    taskId: string,
    onProgress?: ProgressCallback,
    transactionId?: string
  ): Promise<AgentLoopResponse> {
    const maxPolls = apiConfig.polling.maxPolls;
    let pollCount = 0;
    
    while (pollCount < maxPolls) {
      try {
        // Wait before polling to avoid overloading the server
        await new Promise(resolve => setTimeout(resolve, apiConfig.polling.interval));
        
        const response = await this.get<TaskStatusResponse>(`${apiConfig.endpoints.taskStatus}/${taskId}`);
        const status = response.data;
        
        // Update progress based on task status
        if (status.progress !== null && status.progress !== undefined && onProgress) {
          // Map server progress (0-1) to our scale (20-90)
          const min = apiConfig.progressScaling.agentProcessing.min;
          const max = apiConfig.progressScaling.agentProcessing.max;
          const scaledProgress = min + status.progress * (max - min);
          
          onProgress(
            scaledProgress, 
            status.message || `Generazione del report in corso (${Math.round(status.progress * 100)}%)...`,
            transactionId
          );
        }
        
        // Check if the task is complete
        if (status.status === 'completed' && status.result) {
          // Convert snake_case to camelCase for the frontend
          const adaptedResult = adaptApiResponse<AgentLoopResponse>(status.result);
          
          // Update progress to indicate success
          if (onProgress) {
            onProgress(100, 'Generazione completata con successo', transactionId);
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
        // Network error handling - try to recover from transient errors
        if (this.isNetworkError(error) && pollCount < maxPolls) {
          logger.warn(`Network error during polling (attempt ${pollCount + 1}), retrying:`, error);
          pollCount++;
          
          // Notify about the interruption
          if (onProgress) {
            onProgress(
              20, // Keep the same progress level during network errors
              `Interruzione di rete, nuovo tentativo in corso... (${pollCount}/${maxPolls})`,
              transactionId
            );
          }
          
          // Wait a bit longer before retrying after a network error
          await new Promise(resolve => setTimeout(resolve, apiConfig.polling.interval * 2));
          continue;
        }
        
        logger.error('Error polling task status:', error);
        throw error;
      }
    }
    
    throw new Error('Timeout: Task took too long to complete');
  }

  /**
   * Determine if an error is likely a network error
   * @param error The error to check
   * @returns Boolean indicating if the error is a network error
   */
  private isNetworkError(error: any): boolean {
    return (
      error.message === 'Network Error' ||
      error.message === 'Failed to fetch' ||
      error.message === 'The Internet connection appears to be offline.' ||
      error.message === 'The request timed out.' ||
      error.message.includes('timeout') ||
      error.message.includes('network')
    );
  }

  /**
   * Get a report by its ID
   */
  async getReport(reportId: string): Promise<Report> {
    try {
      return await apiClient.get<Report>(`/api/reports/${reportId}`);
    } catch (error) {
      logger.error('Error fetching report:', error);
      throw error;
    }
  }

  /**
   * Get all versions of a report
   */
  async getReportVersions(reportId: string): Promise<VersionHistoryResponse> {
    try {
      return await apiClient.get<VersionHistoryResponse>(`/api/reports/${reportId}/versions`);
    } catch (error) {
      logger.error('Error fetching report versions:', error);
      throw error;
    }
  }

  /**
   * Update a report, optionally creating a new version
   */
  async updateReportWithVersion(
    reportId: string, 
    content: string,
    description: string = 'Updated report content'
  ): Promise<Report> {
    try {
      return await apiClient.put<Report>(`/api/reports/${reportId}`, {
        content,
        create_version: true,
        changes_description: description
      });
    } catch (error) {
      logger.error('Error updating report:', error);
      throw error;
    }
  }

  /**
   * Revert to a specific version of a report
   */
  async revertToVersion(reportId: string, versionNumber: number): Promise<Report> {
    try {
      return await apiClient.post<Report>(`/api/reports/${reportId}/revert`, {
        version_number: versionNumber
      });
    } catch (error) {
      logger.error('Error reverting to version:', error);
      throw error;
    }
  }

  /**
   * Submit report for refinement with AI
   */
  async refineReport(
    reportId: string, 
    content: string, 
    instructions: string
  ): Promise<{ task_id: string }> {
    try {
      return await apiClient.post<{ task_id: string }>('/api/agent-loop/refine-report', {
        report_id: reportId,
        content,
        instructions
      });
    } catch (error) {
      logger.error('Error submitting report for refinement:', error);
      throw error;
    }
  }

  /**
   * Export report to a specified format
   */
  async exportReport(
    reportId: string, 
    format: 'docx' | 'pdf' = 'docx'
  ): Promise<{ download_url: string }> {
    try {
      return await apiClient.get<{ download_url: string }>(
        `/api/reports/${reportId}/export?format=${format}`
      );
    } catch (error) {
      logger.error('Error exporting report:', error);
      throw error;
    }
  }

  /**
   * Download a report directly
   */
  async downloadReport(
    reportId: string, 
    format: 'docx' | 'pdf' = 'docx',
    onProgress?: (progress: number) => void
  ): Promise<void> {
    try {
      const fileName = `report-${reportId}.${format}`;
      await apiClient.downloadFile(
        `/api/reports/${reportId}/download?format=${format}`,
        fileName,
        onProgress
      );
    } catch (error) {
      logger.error('Error downloading report:', error);
      throw error;
    }
  }

  subscribeToTaskEvents(taskId: string, onEvent: (event: any) => void, onError?: (error: any) => void): () => void {
    const eventSource = new EventSource(`/api/agent-loop/task-events/${taskId}`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onEvent(data);
      } catch (error) {
        onError?.(error);
      }
    };

    eventSource.onerror = (error) => {
      onError?.(error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }
}

// Export a singleton instance
export const reportService = new ReportService(); 