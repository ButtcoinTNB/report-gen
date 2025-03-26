import axios, { 
  AxiosInstance, 
  AxiosRequestConfig, 
  AxiosResponse, 
  AxiosError,
  CancelTokenSource,
  Cancel
} from 'axios';
import { useState, useEffect, useCallback } from 'react';
import { backOff } from 'exponential-backoff';
import { getApiBaseUrl } from '../utils/environment';
import { logger } from '../utils/logger';
import errorHandler, { 
  ErrorCategory, 
  ErrorSeverity,
  createError,
  createNetworkError,
  createTimeoutError
} from '../utils/errorHandler';

// Custom error types for better error handling
export class APIError extends Error {
  status: number;
  data: any;
  
  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TimeoutError';
  }
}

// API Response format
export interface APIResponse<T = any> {
  data: T;
  status: number;
  headers: any;
}

// Retry configuration
interface RetryConfig {
  maxRetries: number;
  initialDelayMs: number;
  maxDelayMs: number;
  backoffFactor: number;
  shouldRetry: (error: AxiosError) => boolean;
}

// Default retry configuration
const defaultRetryConfig: RetryConfig = {
  maxRetries: 3,
  initialDelayMs: 1000,
  maxDelayMs: 10000,
  backoffFactor: 2,
  shouldRetry: (error: AxiosError) => {
    // Retry on network errors, timeouts, and 5xx server errors
    const status = error.response?.status;
    return (
      !error.response || // Network error
      error.code === 'ECONNABORTED' || // Timeout
      (status && status >= 500 && status < 600) // Server error
    );
  }
};

// Active request cancellation tokens
const activeRequests = new Map<string, CancelTokenSource>();

/**
 * Core API client for interacting with the backend
 */
export class APIClient {
  private axiosInstance: AxiosInstance;
  private retryConfig: RetryConfig;
  private baseUrl: string;
  private authToken?: string;
  private cancelTokenSources = new Map<string, CancelTokenSource>();
  
  constructor(baseURL: string = '', retryConfig: Partial<RetryConfig> = {}) {
    this.baseUrl = getApiBaseUrl();
    this.axiosInstance = axios.create({
      baseURL,
      timeout: 30000, // 30 seconds default timeout
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    });
    
    this.retryConfig = {
      ...defaultRetryConfig,
      ...retryConfig
    };
    
    // Add request interceptor
    this.axiosInstance.interceptors.request.use((config) => {
      // Add auth token if available
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }
  
  /**
   * Set the authentication token for API requests
   */
  setAuthToken(token: string) {
    this.authToken = token;
    this.axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }
  
  /**
   * Clear the authentication token
   */
  clearAuthToken() {
    this.authToken = undefined;
    delete this.axiosInstance.defaults.headers.common['Authorization'];
  }
  
  /**
   * Get the authentication token
   */
  getAuthToken(): string | undefined {
    return this.authToken;
  }
  
  /**
   * Make a GET request to the API
   */
  async get<T>(endpoint: string, config: AxiosRequestConfig = {}): Promise<T> {
    return this.request<T>({
      ...config,
      method: 'GET',
      url: endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`
    });
  }
  
  /**
   * Make a POST request to the API
   */
  async post<T>(endpoint: string, data?: any, config: AxiosRequestConfig = {}): Promise<T> {
    return this.request<T>({
      ...config,
      method: 'POST',
      url: endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`,
      data
    });
  }
  
  /**
   * Make a PUT request to the API
   */
  async put<T>(endpoint: string, data?: any, config: AxiosRequestConfig = {}): Promise<T> {
    return this.request<T>({
      ...config,
      method: 'PUT',
      url: endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`,
      data
    });
  }
  
  /**
   * Make a DELETE request to the API
   */
  async delete<T>(endpoint: string, config: AxiosRequestConfig = {}): Promise<T> {
    return this.request<T>({
      ...config,
      method: 'DELETE',
      url: endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`
    });
  }
  
  /**
   * Make an API request with automatic retry for transient errors
   */
  private async request<T>(config: AxiosRequestConfig): Promise<T> {
    // Generate request ID for tracking/cancellation
    const requestId = `${config.method || 'GET'}-${config.url}-${Date.now()}`;
    
    // Create cancel token
    const source = axios.CancelToken.source();
    config.cancelToken = source.token;
    
    // Store cancel token for potential cancellation
    activeRequests.set(requestId, source);
    
    try {
      // If data is FormData, remove Content-Type header to let browser set it
      if (config.data instanceof FormData) {
        delete this.axiosInstance.defaults.headers['Content-Type'];
        if (config.headers) {
          delete config.headers['Content-Type'];
        }
      }
      
      // Implement retry logic with exponential backoff
      const response = await backOff(
        () => this.axiosInstance.request<T>(config),
        {
          numOfAttempts: this.retryConfig.maxRetries,
          startingDelay: this.retryConfig.initialDelayMs,
          maxDelay: this.retryConfig.maxDelayMs,
          retry: (error: any) => {
            if (axios.isCancel(error)) {
              return false; // Don't retry cancelled requests
            }
            
            // Use retry config to determine if we should retry
            return this.retryConfig.shouldRetry(error);
          },
          jitter: 'full' // Add randomness to prevent thundering herd
        }
      );
      
      // Restore default Content-Type header
      if (config.data instanceof FormData) {
        this.axiosInstance.defaults.headers['Content-Type'] = 'application/json';
      }
      
      return response.data;
    } catch (error) {
      // Restore default Content-Type header in case of error
      if (config.data instanceof FormData) {
        this.axiosInstance.defaults.headers['Content-Type'] = 'application/json';
      }
      
      // Convert error to appropriate type with our error handler
      if (axios.isCancel(error)) {
        throw createError(error, {
          message: 'Request cancelled',
          category: ErrorCategory.INTERNAL,
          severity: ErrorSeverity.INFO,
          retryable: false
        });
      }
      
      if (error.code === 'ECONNABORTED') {
        throw createTimeoutError('Request timed out', error);
      }
      
      if (!error.response) {
        throw createNetworkError('Network error', error);
      }
      
      // Handle API errors with standardized error format
      const appError = createError(error, {
        category: ErrorCategory.API,
        context: {
          url: config.url,
          method: config.method,
          requestId
        }
      });
      
      // Log the error through our error handler
      errorHandler.handleError(appError);
      
      // Re-throw the error
      throw appError;
    } finally {
      // Clean up cancel token
      activeRequests.delete(requestId);
    }
  }
  
  /**
   * Upload a file with progress tracking using chunked upload
   */
  async uploadFile<T>(
    endpoint: string,
    file: File,
    additionalData: Record<string, any> = {},
    onProgress?: (progress: number) => void
  ): Promise<T> {
    // Initialize upload
    const formData = new FormData();
    formData.append('filename', file.name);
    formData.append('fileSize', file.size.toString());
    formData.append('mimeType', file.type);
    
    // Add additional data as form fields directly
    Object.entries(additionalData).forEach(([key, value]) => {
      // Don't stringify the value, send it as is
      formData.append(key, value);
    });

    const initResponse = await this.post<{
      uploadId: string;
      chunkSize: number;
      totalChunks: number;
      uploadedChunks: number[];
    }>(`${endpoint}/initialize`, formData);

    const { uploadId, chunkSize, totalChunks } = initResponse;
    let uploadedChunks = 0;

    // Upload chunks
    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      const chunk = file.slice(start, end);

      const chunkFormData = new FormData();
      chunkFormData.append('uploadId', uploadId);
      chunkFormData.append('chunkIndex', i.toString());
      chunkFormData.append('start', start.toString());
      chunkFormData.append('end', end.toString());
      chunkFormData.append('chunk', chunk);

      await this.post(
        `${endpoint}/chunk`,
        chunkFormData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          }
        }
      );

      uploadedChunks++;
      if (onProgress) {
        onProgress((uploadedChunks / totalChunks) * 100);
      }
    }

    // Finalize upload
    const finalizeFormData = new FormData();
    finalizeFormData.append('uploadId', uploadId);
    finalizeFormData.append('filename', file.name);
    if (additionalData.reportId) {
      finalizeFormData.append('reportId', additionalData.reportId);
    }

    return this.post<T>(
      `${endpoint}/finalize`,
      finalizeFormData
    );
  }
  
  /**
   * Download a file
   */
  async downloadFile(
    endpoint: string,
    filename: string,
    onProgress?: (progress: number) => void
  ): Promise<void> {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
    
    const config: AxiosRequestConfig = {
      responseType: 'blob',
      onDownloadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    };
    
    const response = await this.axiosInstance.get(url, config);
    
    // Create a download link and trigger the download
    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  }
  
  /**
   * Cancel all active requests
   */
  cancelAllRequests(message: string = 'Request cancelled by user') {
    activeRequests.forEach((source) => {
      source.cancel(message);
    });
    activeRequests.clear();
  }
  
  /**
   * Cancel a specific request by URL pattern
   */
  cancelRequest(urlPattern: string | RegExp, message: string = 'Request cancelled by user') {
    activeRequests.forEach((source, key) => {
      if (typeof urlPattern === 'string') {
        if (key.includes(urlPattern)) {
          source.cancel(message);
          activeRequests.delete(key);
        }
      } else {
        if (urlPattern.test(key)) {
          source.cancel(message);
          activeRequests.delete(key);
        }
      }
    });
  }

  private async requestWithRetry<T>(
    config: AxiosRequestConfig,
    requestId?: string,
    retryCount = 0
  ): Promise<AxiosResponse<T>> {
    try {
      // Add cancel token if requestId is provided
      if (requestId) {
        const source = axios.CancelToken.source();
        this.cancelTokenSources.set(requestId, source);
        config.cancelToken = source.token;
      }
      
      return await this.axiosInstance.request<T>(config);
    } catch (error: any) {
      if (axios.isCancel(error)) {
        throw new APIError('Request cancelled', 0, error as Error);
      }
      
      if (!error.response) {
        if (error.code === 'ECONNABORTED') {
          throw new TimeoutError('Request timed out');
        }
        throw new NetworkError('Network error');
      }
      
      // API returned an error response
      const apiError = new APIError(
        error.response.data?.message || 'API request failed',
        error.response.status,
        error.response.data
      );
      
      // Check if we should retry
      if (
        retryCount < this.retryConfig.maxRetries &&
        this.retryConfig.shouldRetry(error)
      ) {
        // Calculate backoff delay with exponential backoff and jitter
        const delay = Math.min(
          this.retryConfig.initialDelayMs * Math.pow(this.retryConfig.backoffFactor, retryCount),
          this.retryConfig.maxDelayMs
        );
        const jitteredDelay = delay * (0.5 + Math.random() * 0.5); // Add 0-50% jitter
        
        console.warn(`Retrying request (${retryCount + 1}/${this.retryConfig.maxRetries}) after ${jitteredDelay}ms`);
        
        // Wait for the delay
        await new Promise(resolve => setTimeout(resolve, jitteredDelay));
        
        // Retry the request
        return this.requestWithRetry<T>(config, requestId, retryCount + 1);
      }
      
      throw apiError;
    } finally {
      // Clean up cancel token
      if (requestId) {
        this.cancelTokenSources.delete(requestId);
      }
    }
  }
}

// Export a singleton instance
export const apiClient = new APIClient(process.env.NEXT_PUBLIC_API_URL);

export default apiClient;

// React hook for using the API client
export const useApiClient = () => {
  return apiClient;
};

// Hook for making API requests with automatic cleanup
export function useApiRequest<T = any>(
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
  url: string,
  options: {
    data?: any;
    config?: AxiosRequestConfig;
    deps?: any[];
    immediate?: boolean;
  } = {}
) {
  const { data: initialData, config, deps = [], immediate = false } = options;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState<Error | null>(null);
  const api = useApiClient();
  
  const requestId = `${method}_${url}_${JSON.stringify(deps)}_${Date.now()}`;
  
  const execute = useCallback(async (execData?: any): Promise<T | null> => {
    setLoading(true);
    setError(null);
    
    try {
      let response;
      const requestData = execData !== undefined ? execData : initialData;
      
      switch (method) {
        case 'GET':
          response = await api.get<T>(url, config);
          break;
        case 'POST':
          response = await api.post<T>(url, requestData, config);
          break;
        case 'PUT':
          response = await api.put<T>(url, requestData, config);
          break;
        case 'DELETE':
          response = await api.delete<T>(url, config);
          break;
        case 'PATCH':
          response = await api.post<T>(url, requestData, config);
          break;
      }
      
      setData(response.data);
      setLoading(false);
      return response.data;
    } catch (err) {
      console.error('API request failed:', err);
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      setLoading(false);
      return null;
    }
  }, [method, url, initialData, config, api]);
  
  // Execute request immediately if immediate is true
  useEffect(() => {
    if (immediate) {
      execute();
    }
    
    // Cancel request on cleanup
    return () => {
      api.cancelRequest(requestId);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  
  return { data, loading, error, execute, cancel: () => api.cancelRequest(requestId) };
} 