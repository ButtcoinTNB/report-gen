import { TIMEOUTS } from '../constants/app';
import { isBrowser, isServer } from './environment';

export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

export const retryWithBackoff = async <T>(
  fn: () => Promise<T>,
  maxRetries = 3
): Promise<T> => {
  let retries = 0;
  while (true) {
    try {
      return await fn();
    } catch (error) {
      if (retries === maxRetries) throw error;
      retries++;
      await new Promise(resolve => 
        setTimeout(resolve, TIMEOUTS.RETRY_DELAY * Math.pow(2, retries - 1))
      );
    }
  }
};

export const isValidUUID = (id: string): boolean => {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(id);
};

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

export const sanitizeFileName = (fileName: string): string => {
  return fileName
    .replace(/[^a-z0-9.-]/gi, '_')
    .replace(/_+/g, '_')
    .toLowerCase();
};

export const generateShareToken = (): string => {
  return `${Date.now()}-${generateUUID()}`;
};

/**
 * Generate a UUID that works in both browser and Node.js environments
 * @returns A UUID or random ID string
 */
export const generateUUID = (): string => {
  if (isBrowser && window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  } else if (isServer) {
    try {
      // Using require to avoid bundling crypto in client
      const nodeCrypto = require('crypto');
      return nodeCrypto.randomUUID();
    } catch (error) {
      // Fallback for older Node versions or if crypto isn't available
      return `id-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
    }
  } else {
    // Fallback for browsers without crypto support
    return `id-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
  }
};

/**
 * Generate a unique filename with timestamp and UUID
 * @returns A unique filename string
 */
export const generateUniqueFilename = (): string => {
  return `${Date.now()}-${generateUUID()}`;
}; 