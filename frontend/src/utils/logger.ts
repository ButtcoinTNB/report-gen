/**
 * Logger utility for consistent logging across the application
 * Automatically controls log output based on environment
 */

// Check if we're in development mode
const isDevelopment = process.env.NODE_ENV !== 'production';

/**
 * Logger singleton with methods for different log levels
 * In production, only error and warn will output to console
 * This complements the Next.js config which also strips console.log in production
 */
export const logger = {
  /**
   * Debug level logging - only appears in development
   */
  debug: (...args: any[]): void => {
    if (isDevelopment) {
      console.log('[DEBUG]', ...args);
    }
  },

  /**
   * Info level logging - only appears in development
   */
  info: (...args: any[]): void => {
    if (isDevelopment) {
      console.info('[INFO]', ...args);
    }
  },

  /**
   * Warning level logging - appears in all environments
   */
  warn: (...args: any[]): void => {
    console.warn('[WARN]', ...args);
  },

  /**
   * Error level logging - appears in all environments
   */
  error: (...args: any[]): void => {
    console.error('[ERROR]', ...args);
  },

  /**
   * Log specific to API requests - only in development
   */
  api: (endpoint: string, ...args: any[]): void => {
    if (isDevelopment) {
      console.log(`[API:${endpoint}]`, ...args);
    }
  },

  /**
   * Performance tracking - only in development
   */
  perf: (label: string, ...args: any[]): void => {
    if (isDevelopment) {
      console.log(`[PERF:${label}]`, ...args);
    }
  }
};

// Default export for easier importing
export default logger; 