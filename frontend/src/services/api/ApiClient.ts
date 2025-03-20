import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { config } from '../../../config';

/**
 * Configuration options for API requests
 */
export interface ApiRequestOptions {
  /** Whether this is a multipart/form-data request */
  isMultipart?: boolean;
  /** Request timeout in milliseconds */
  timeout?: number;
  /** Function to track upload progress */
  onUploadProgress?: (progressEvent: any) => void;
  /** Options for automatic retry on failure */
  retryOptions?: {
    /** Maximum number of retry attempts */
    maxRetries?: number;
    /** Delay between retries in milliseconds */
    retryDelay?: number;
    /** Function called when a retry is attempted */
    onRetry?: (attempt: number, maxRetries: number) => void;
  };
}

/**
 * Configuration for initializing the API client
 */
export interface ApiClientConfig {
  /** Base URL for API requests */
  baseUrl: string;
  /** Default timeout in milliseconds */
  defaultTimeout?: number;
  /** Default number of retry attempts */
  defaultRetries?: number;
  /** Default delay between retries in milliseconds */
  defaultRetryDelay?: number;
}

/**
 * Base class for all API service clients
 * Provides common functionality for API requests with retry capabilities
 */
export class ApiClient {
  protected axios: AxiosInstance;
  protected baseUrl: string;
  protected defaultOptions: {
    timeout: number;
    retries: number;
    retryDelay: number;
  };

  /**
   * Create a new API client
   * @param clientConfig Configuration for this API client
   */
  constructor(clientConfig: ApiClientConfig) {
    this.baseUrl = clientConfig.baseUrl;
    this.defaultOptions = {
      timeout: clientConfig.defaultTimeout || 60000,
      retries: clientConfig.defaultRetries || 3,
      retryDelay: clientConfig.defaultRetryDelay || 1000
    };

    this.axios = axios.create({
      baseURL: this.baseUrl
    });
  }

  /**
   * Make a GET request with automatic retries
   * @param path Path to append to the base URL
   * @param options Request options including retry configuration
   * @returns Promise with the API response
   */
  protected async get<T = any>(path: string, options: ApiRequestOptions = {}): Promise<AxiosResponse<T>> {
    const { retryOptions, ...requestOptions } = options;
    const url = path.startsWith('/') ? path : `/${path}`;
    
    const config = this.createRequestConfig(requestOptions);
    
    return this.withRetry<T>(() => this.axios.get<T>(url, config), retryOptions);
  }

  /**
   * Make a POST request with automatic retries
   * @param path Path to append to the base URL
   * @param data Request payload
   * @param options Request options including retry configuration
   * @returns Promise with the API response
   */
  protected async post<T = any>(path: string, data: any, options: ApiRequestOptions = {}): Promise<AxiosResponse<T>> {
    const { retryOptions, ...requestOptions } = options;
    const url = path.startsWith('/') ? path : `/${path}`;
    
    const config = this.createRequestConfig(requestOptions);
    
    return this.withRetry<T>(() => this.axios.post<T>(url, data, config), retryOptions);
  }

  /**
   * Make a PUT request with automatic retries
   * @param path Path to append to the base URL
   * @param data Request payload
   * @param options Request options including retry configuration
   * @returns Promise with the API response
   */
  protected async put<T = any>(path: string, data: any, options: ApiRequestOptions = {}): Promise<AxiosResponse<T>> {
    const { retryOptions, ...requestOptions } = options;
    const url = path.startsWith('/') ? path : `/${path}`;
    
    const config = this.createRequestConfig(requestOptions);
    
    return this.withRetry<T>(() => this.axios.put<T>(url, data, config), retryOptions);
  }

  /**
   * Make a DELETE request with automatic retries
   * @param path Path to append to the base URL
   * @param options Request options including retry configuration
   * @returns Promise with the API response
   */
  protected async delete<T = any>(path: string, options: ApiRequestOptions = {}): Promise<AxiosResponse<T>> {
    const { retryOptions, ...requestOptions } = options;
    const url = path.startsWith('/') ? path : `/${path}`;
    
    const config = this.createRequestConfig(requestOptions);
    
    return this.withRetry<T>(() => this.axios.delete<T>(url, config), retryOptions);
  }

  /**
   * Create axios request configuration
   * @param options Request options
   * @returns Axios request configuration
   */
  private createRequestConfig(options: ApiRequestOptions): AxiosRequestConfig {
    const { isMultipart, timeout, onUploadProgress } = options;
    
    const headers = isMultipart 
      ? { 'Content-Type': 'multipart/form-data', 'Accept': 'application/json' }
      : { 'Content-Type': 'application/json', 'Accept': 'application/json' };
    
    const config: AxiosRequestConfig = {
      headers,
      timeout: timeout || this.defaultOptions.timeout,
    };
    
    if (isMultipart && onUploadProgress) {
      config.onUploadProgress = onUploadProgress;
    }
    
    return config;
  }

  /**
   * Make a request with automatic retries for improved network resilience
   * @param requestFn Function that returns a promise (axios request)
   * @param options Options for the retry mechanism
   * @returns Promise with the response
   */
  private async withRetry<T>(
    requestFn: () => Promise<AxiosResponse<T>>,
    options: ApiRequestOptions['retryOptions'] = {}
  ): Promise<AxiosResponse<T>> {
    const maxRetries = options?.maxRetries ?? this.defaultOptions.retries;
    const retryDelay = options?.retryDelay ?? this.defaultOptions.retryDelay;
    const onRetry = options?.onRetry;
    
    let lastError: any;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        // On first attempt or subsequent retries
        return await requestFn();
      } catch (error: any) {
        lastError = error;
        
        // Only retry on network errors or 5xx errors, not on 4xx client errors
        const shouldRetry = (
          error.code === 'ECONNABORTED' || 
          error.code === 'ERR_NETWORK' ||
          (error.response && error.response.status >= 500 && error.response.status < 600)
        );
        
        // If we've reached max retries or shouldn't retry this error, throw
        if (attempt >= maxRetries || !shouldRetry) {
          throw error;
        }
        
        // Log retry attempt
        console.log(`Request failed, retrying (${attempt + 1}/${maxRetries})...`, error);
        
        // Call onRetry callback if provided
        if (onRetry) {
          onRetry(attempt + 1, maxRetries);
        }
        
        // Wait before retrying
        await new Promise(resolve => setTimeout(resolve, retryDelay * (attempt + 1)));
      }
    }
    
    // This should never be reached due to the throw in the loop
    throw lastError;
  }
}

/**
 * Create an API client instance
 * @param endpoint The API endpoint to connect to
 * @param options Optional configuration
 * @returns API client instance
 */
export function createApiClient(
  endpoint: string,
  options: {
    retries?: number;
    retryDelay?: number;
    timeout?: number;
  } = {}
): ApiClient {
  let baseUrl: string;
  
  // If endpoint is a full URL, use it directly
  if (endpoint.startsWith('http')) {
    baseUrl = endpoint;
  } 
  // If it's a relative URL, prepend the API_URL
  else if (endpoint.startsWith('/')) {
    baseUrl = `${config.API_URL}${endpoint}`;
  }
  // Otherwise treat it as an endpoint key from the config
  else {
    // Add explicit type check to ensure endpoint is a valid key in config.endpoints
    const endpointUrl = config.endpoints && typeof config.endpoints === 'object' && endpoint in config.endpoints
      ? (config.endpoints as Record<string, string>)[endpoint]
      : null;
    
    if (endpointUrl) {
      baseUrl = endpointUrl;
    } else {
      console.error(`No endpoint configured for '${endpoint}'`);
      // Fallback to API_URL as base
      baseUrl = `${config.API_URL}/${endpoint}`;
    }
  }
  
  return new ApiClient({
    baseUrl,
    defaultRetries: options.retries,
    defaultRetryDelay: options.retryDelay,
    defaultTimeout: options.timeout
  });
} 