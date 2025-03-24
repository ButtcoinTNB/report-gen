/**
 * Environment utilities for safely determining execution context
 */

/**
 * Determine if code is running in a browser environment
 * Checks both window and document to be extra safe
 */
export const isBrowser = typeof window !== 'undefined' && window.document !== undefined;

/**
 * Determine if code is running in a server environment
 */
export const isServer = !isBrowser;

/**
 * Determine if we're in a development environment
 */
export const isDevelopment = typeof process !== 'undefined' && process.env && process.env.NODE_ENV === 'development';

/**
 * Determine if we're in a production environment
 */
export const isProduction = typeof process !== 'undefined' && process.env && process.env.NODE_ENV === 'production';

/**
 * Checks if we should use mock data instead of real API/Supabase calls
 * This is determined by:
 * 1. Development mode AND
 * 2. NEXT_PUBLIC_USE_MOCKS environment variable set to 'true'
 */
export const useMocks = isDevelopment && typeof process !== 'undefined' && 
  process.env && process.env.NEXT_PUBLIC_USE_MOCKS === 'true';

/**
 * Safely access window object (only in browser)
 * @param callback Function to execute with window object
 * @param fallback Fallback value if not in browser
 */
export function withWindow<T>(callback: (w: Window) => T, fallback: T): T {
  if (isBrowser) {
    try {
      return callback(window);
    } catch (error) {
      console.error('Window access error:', error);
      return fallback;
    }
  }
  return fallback;
}

/**
 * Safely access localStorage (only in browser)
 * @param callback Function to execute with localStorage
 * @param fallback Fallback value if not in browser
 */
export function withLocalStorage<T>(callback: (storage: Storage) => T, fallback: T): T {
  if (isBrowser && window.localStorage) {
    try {
      return callback(window.localStorage);
    } catch (error) {
      console.error('localStorage error:', error);
      return fallback;
    }
  }
  return fallback;
}

/**
 * Gets the base URL for the app
 * @returns The base URL of the application
 */
export const getBaseUrl = (): string => {
  if (isBrowser) {
    return window.location.origin;
  }

  // When on the server, use environment variables
  const url = typeof process !== 'undefined' && process.env ? 
    (process.env.VERCEL_URL || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000') :
    'http://localhost:3000';

  // Return the URL with https if not localhost
  return url.startsWith('http') ? url : `https://${url}`;
};

/**
 * Detect client browser locale for internationalization
 * @returns The detected locale or default ('it-IT')
 */
export const getClientLocale = (): string => {
  if (!isBrowser) return 'it-IT'; // Default to Italian
  
  try {
    return navigator.language || 'it-IT';
  } catch {
    return 'it-IT';
  }
};

/**
 * Get base URL for API calls
 */
export function getApiBaseUrl(): string {
  if (isServer) {
    // Server-side rendering - use the environment variable
    return typeof process !== 'undefined' && process.env ? 
      (process.env.NEXT_PUBLIC_API_URL || '') : '';
  }
  
  // Client-side - use the public environment variable
  return typeof process !== 'undefined' && process.env ? 
    (process.env.NEXT_PUBLIC_API_URL || '') : '';
} 