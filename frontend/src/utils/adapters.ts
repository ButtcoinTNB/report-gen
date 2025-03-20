/**
 * adapters.ts
 * Utility functions to convert between snake_case (backend/Python) and camelCase (frontend/TypeScript) 
 */

import { logger } from './logger';

/**
 * Convert a string from snake_case to camelCase
 * Examples: 
 *   'hello_world' -> 'helloWorld'
 *   'report_id' -> 'reportId'
 *   'preview_url' -> 'previewUrl'
 */
export function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Convert a string from camelCase to snake_case
 * Examples:
 *   'helloWorld' -> 'hello_world'
 *   'reportId' -> 'report_id'
 *   'previewUrl' -> 'preview_url'
 */
export function camelToSnake(str: string): string {
  return str.replace(/([A-Z])/g, (_, letter) => `_${letter.toLowerCase()}`);
}

/**
 * Transform an object's keys from snake_case to camelCase
 * @param obj The snake_case object to transform
 * @returns A new object with camelCase keys
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
 * @param obj The camelCase object to transform
 * @returns A new object with snake_case keys
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