/**
 * Environment utilities for safely determining execution context
 */

/**
 * Check if code is running in a browser environment
 * This safely detects if window and navigator are available
 */
export const isBrowser = typeof window !== 'undefined' && typeof navigator !== 'undefined';

/**
 * Check if code is running in a server environment (Node.js)
 */
export const isServer = !isBrowser;

/**
 * Check if code is running in development mode
 */
export const isDevelopment = process.env.NODE_ENV === 'development';

/**
 * Checks if we should use mock data instead of real API/Supabase calls
 * This is determined by:
 * 1. Development mode AND
 * 2. NEXT_PUBLIC_USE_MOCKS environment variable set to 'true'
 */
export const useMocks = isDevelopment && process.env.NEXT_PUBLIC_USE_MOCKS === 'true';

/**
 * Safe wrapper for accessing browser APIs
 * @param callback Function that uses browser APIs
 * @param fallback Value to return when not in browser
 */
export function browserOnly<T>(callback: () => T, fallback: T): T {
  return isBrowser ? callback() : fallback;
}

/**
 * Safe wrapper for running browser-only code
 * @param callback Function to execute only in browser environment
 */
export function runInBrowser(callback: () => void): void {
  if (isBrowser) {
    callback();
  }
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
  const url = process.env.VERCEL_URL || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

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