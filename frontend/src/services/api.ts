import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';
import { backOff } from 'exponential-backoff';

// Error types
export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public code: string,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
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

// API Response type
interface APIResponse<T> {
  data: T;
  message?: string;
}

// API Client class
export class APIClient {
  private client: AxiosInstance;
  private retryConfig = {
    numOfAttempts: 3,
    startingDelay: 1000,
    timeMultiple: 2,
    maxDelay: 10000,
  };

  constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || '') {
    this.client = axios.create({
      baseURL,
      timeout: 30000, // 30 seconds
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      this.handleResponseError
    );
  }

  private async handleResponseError(error: AxiosError): Promise<never> {
    if (error.response) {
      // Server responded with error
      const data = error.response.data as any;
      throw new APIError(
        data.error?.message || 'Unknown error',
        error.response.status,
        data.error?.code || 'UNKNOWN_ERROR',
        data.error?.details
      );
    } else if (error.request) {
      // Request made but no response
      if (error.code === 'ECONNABORTED') {
        throw new TimeoutError('Request timed out');
      }
      throw new NetworkError('Network error occurred');
    } else {
      // Error setting up request
      throw new Error('Failed to make request');
    }
  }

  private async makeRequest<T>(
    config: AxiosRequestConfig,
    shouldRetry: boolean = true
  ): Promise<APIResponse<T>> {
    try {
      if (shouldRetry) {
        const response = await backOff(
          () => this.client.request<APIResponse<T>>(config),
          {
            ...this.retryConfig,
            retry: (e: any) => {
              if (e instanceof APIError) {
                // Only retry on 5xx errors or specific 4xx errors
                return e.status >= 500 || [429, 408].includes(e.status);
              }
              return true; // Retry on network errors
            },
          }
        );
        return response.data;
      } else {
        const response = await this.client.request<APIResponse<T>>(config);
        return response.data;
      }
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Unknown error occurred');
    }
  }

  // GET request
  async get<T>(
    url: string,
    params?: Record<string, any>,
    config: Partial<AxiosRequestConfig> = {}
  ): Promise<T> {
    const response = await this.makeRequest<T>({
      ...config,
      method: 'GET',
      url,
      params,
    });
    return response.data;
  }

  // POST request
  async post<T>(
    url: string,
    data?: any,
    config: Partial<AxiosRequestConfig> = {}
  ): Promise<T> {
    const response = await this.makeRequest<T>({
      ...config,
      method: 'POST',
      url,
      data,
    });
    return response.data;
  }

  // PUT request
  async put<T>(
    url: string,
    data?: any,
    config: Partial<AxiosRequestConfig> = {}
  ): Promise<T> {
    const response = await this.makeRequest<T>({
      ...config,
      method: 'PUT',
      url,
      data,
    });
    return response.data;
  }

  // DELETE request
  async delete<T>(
    url: string,
    config: Partial<AxiosRequestConfig> = {}
  ): Promise<T> {
    const response = await this.makeRequest<T>({
      ...config,
      method: 'DELETE',
      url,
    });
    return response.data;
  }

  // Upload file with progress
  async uploadFile<T>(
    url: string,
    file: File,
    onProgress?: (progress: number) => void,
    config: Partial<AxiosRequestConfig> = {}
  ): Promise<T> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.makeRequest<T>(
      {
        ...config,
        method: 'POST',
        url,
        data: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = (progressEvent.loaded / progressEvent.total) * 100;
            onProgress(progress);
          }
        },
      },
      false // Don't retry file uploads automatically
    );

    return response.data;
  }

  // Download file with progress
  async downloadFile(
    url: string,
    filename: string,
    onProgress?: (progress: number) => void,
    config: Partial<AxiosRequestConfig> = {}
  ): Promise<void> {
    const response = await this.client.get(url, {
      ...config,
      responseType: 'blob',
      onDownloadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = (progressEvent.loaded / progressEvent.total) * 100;
          onProgress(progress);
        }
      },
    });

    // Create download link
    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }
}

// Create and export singleton instance
export const api = new APIClient();
export default api; 