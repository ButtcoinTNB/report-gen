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