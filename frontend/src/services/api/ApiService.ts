import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

export interface ApiRequestOptions extends AxiosRequestConfig {
  retryOptions?: {
    maxRetries: number;
    retryDelay?: number;
  };
}

export class ApiService {
  protected client: AxiosInstance;

  constructor() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    
    this.client = axios.create({
      baseURL: apiUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for auth token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }
  
  // Add HTTP methods
  protected async get<T>(url: string, options?: ApiRequestOptions): Promise<AxiosResponse<T>> {
    return this.client.get<T>(url, options);
  }
  
  protected async post<T>(url: string, data?: any, options?: ApiRequestOptions): Promise<AxiosResponse<T>> {
    return this.client.post<T>(url, data, options);
  }
  
  protected async put<T>(url: string, data?: any, options?: ApiRequestOptions): Promise<AxiosResponse<T>> {
    return this.client.put<T>(url, data, options);
  }
  
  protected async delete<T>(url: string, options?: ApiRequestOptions): Promise<AxiosResponse<T>> {
    return this.client.delete<T>(url, options);
  }
} 