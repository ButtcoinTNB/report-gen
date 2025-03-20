import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { config } from '../../../config';
import { logger } from '../../utils/logger';
import { adaptApiRequest, adaptApiResponse, camelToSnakeObject, snakeToCamelObject } from '../../utils/adapters';

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
  /** Whether to skip automatic conversion of request/response data */
  skipConversion?: boolean;
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
 * Frontend-friendly version of API client config with camelCase
 */
export interface ApiClientConfigCamel {
  baseUrl: string;
  defaultTimeout?: number;
  defaultRetries?: number;
  defaultRetryDelay?: number;
}

/**
 * Base class for all API service clients
 * Provides common functionality for API requests with retry capabilities
 * Automatically converts between snake_case (backend) and camelCase (frontend)
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

    // Add request interceptor to convert camelCase to snake_case
    this.axios.interceptors.request.use((config) => {
      // Skip conversion for multipart/form-data requests
      if (config.headers?.['Content-Type'] === 'multipart/form-data') {
        return config;
      }
      
      // Convert request data from camelCase to snake_case if it exists
      if (config.data && typeof config.data === 'object' && !(config as any).skipConversion) {
        config.data = camelToSnakeObject(config.data);
      }
      
      return config;
    });

    // Add response interceptor to convert snake_case to camelCase
    this.axios.interceptors.response.use((response) => {
      // Skip conversion if requested
      if ((response.config as any).skipConversion) {
        return response;
      }
      
      // Convert response data from snake_case to camelCase
      if (response.data && typeof response.data === 'object') {
        response.data = snakeToCamelObject(response.data);
      }
      
      return response;
    });
  }

  /**
   * Make a GET request with automatic retries
   * @param path Path to append to the base URL
   * @param options Request options including retry configuration
   * @returns Promise with the API response
   */
  protected async get<T = any, R = any>(path: string, options: ApiRequestOptions = {}): Promise<AxiosResponse<T>> {
    const { retryOptions, ...requestOptions } = options;
    const url = path.startsWith('/') ? path : `/${path}`;
    
    const config = this.createRequestConfig(requestOptions);
    
    const response = await this.withRetry<R>(() => this.axios.get<R>(url, config), retryOptions);
    
    // If skipConversion is true, return response as is
    if (options.skipConversion) {
      return response as unknown as AxiosResponse<T>;
    }
    
    // Otherwise, convert the response data to the expected type T
    return {
      ...response,
      data: adaptApiResponse<T>(response.data)
    };
  }

  /**
   * Make a POST request with automatic retries
   * @param path Path to append to the base URL
   * @param data Request payload
   * @param options Request options including retry configuration
   * @returns Promise with the API response
   */
  protected async post<T = any, R = any>(
    path: string, 
    data: any, 
    options: ApiRequestOptions = {}
  ): Promise<AxiosResponse<T>> {
    const { retryOptions, ...requestOptions } = options;
    const url = path.startsWith('/') ? path : `/${path}`;
    
    const config = this.createRequestConfig(requestOptions);
    
    // Convert request data if needed
    const requestData = options.skipConversion ? data : adaptApiRequest(data);
    
    const response = await this.withRetry<R>(() => this.axios.post<R>(url, requestData, config), retryOptions);
    
    // If skipConversion is true, return response as is
    if (options.skipConversion) {
      return response as unknown as AxiosResponse<T>;
    }
    
    // Otherwise, convert the response data to the expected type T
    return {
      ...response,
      data: adaptApiResponse<T>(response.data)
    };
  }

  /**
   * Make a PUT request with automatic retries
   * @param path Path to append to the base URL
   * @param data Request payload
   * @param options Request options including retry configuration
   * @returns Promise with the API response
   */
  protected async put<T = any, R = any>(
    path: string, 
    data: any, 
    options: ApiRequestOptions = {}
  ): Promise<AxiosResponse<T>> {
    const { retryOptions, ...requestOptions } = options;
    const url = path.startsWith('/') ? path : `/${path}`;
    
    const config = this.createRequestConfig(requestOptions);
    
    // Convert request data if needed
    const requestData = options.skipConversion ? data : adaptApiRequest(data);
    
    const response = await this.withRetry<R>(() => this.axios.put<R>(url, requestData, config), retryOptions);
    
    // If skipConversion is true, return response as is
    if (options.skipConversion) {
      return response as unknown as AxiosResponse<T>;
    }
    
    // Otherwise, convert the response data to the expected type T
    return {
      ...response,
      data: adaptApiResponse<T>(response.data)
    };
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
        logger.api(this.baseUrl, `Request failed, retrying (${attempt + 1}/${maxRetries})...`, error);
        
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
 * 
 * Factory function to create an ApiClient instance with appropriate configuration.
 * This function handles endpoint resolution and configuration standardization.
 * 
 * @example
 * // Create a client for the report API
 * const reportClient = createApiClient('report', { retries: 3, retryDelay: 2000 });
 * 
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
  // Convert options to snake_case for the backend config format
  const snakeOptions = adaptApiRequest(options);
  
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
      logger.error(`No endpoint configured for '${endpoint}'`);
      // Fallback to API_URL as base
      baseUrl = `${config.API_URL}/${endpoint}`;
    }
  }
  
  // Create ApiClientConfig using the properly adapted options
  const clientConfig: ApiClientConfig = {
    baseUrl,
    defaultRetries: options.retries,
    defaultRetryDelay: options.retryDelay,
    defaultTimeout: options.timeout
  };
  
  return new ApiClient(clientConfig);
} 