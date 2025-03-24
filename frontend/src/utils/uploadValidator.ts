/**
 * Utilities for validating file uploads
 */

// Constants
const MAX_FILE_SIZE = 1024 * 1024 * 1024; // 1GB maximum file size

// Allowed MIME types
const ALLOWED_MIME_TYPES = new Set([
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'image/jpeg',
  'image/png',
  'image/gif'
]);

/**
 * Upload-specific error class
 */
export class UploadError extends Error {
  public readonly code: string;
  public readonly details?: string;
  public readonly retry?: boolean;
  
  constructor(message: string, code: string = 'upload_error', details?: string, retry: boolean = false) {
    super(message);
    this.name = 'UploadError';
    this.code = code;
    this.details = details;
    this.retry = retry;
    
    // Ensure instanceof works correctly
    Object.setPrototypeOf(this, UploadError.prototype);
  }
}

/**
 * Validate a file for upload
 * 
 * @param file The file to validate
 * @param options Optional validation options
 * @returns Validation result with validity and any error message
 */
export function validateUploadFile(
  file: File, 
  options: {
    maxSize?: number;
    allowedTypes?: Set<string>;
  } = {}
): { valid: boolean; error?: string } {
  const maxSize = options.maxSize || MAX_FILE_SIZE;
  const allowedTypes = options.allowedTypes || ALLOWED_MIME_TYPES;

  // Check file size
  if (!file) {
    return { valid: false, error: 'No file provided' };
  }
  
  if (file.size <= 0) {
    return { valid: false, error: 'File is empty' };
  }
  
  if (file.size > maxSize) {
    return { valid: false, error: `Maximum file size is ${maxSize / (1024 * 1024)}MB` };
  }
  
  // Check file type
  if (!allowedTypes.has(file.type)) {
    return { valid: false, error: `File type ${file.type || 'unknown'} is not allowed` };
  }
  
  // Check filename
  if (!file.name || file.name.includes('..') || /[<>:"/\\|?*\x00-\x1F]/.test(file.name)) {
    return { valid: false, error: 'Filename contains invalid characters' };
  }
  
  return { valid: true };
}

/**
 * Validate a file and throw an error if invalid
 * 
 * @param file The file to validate
 * @param options Optional validation options
 * @throws UploadError if the file is invalid
 */
export function validateAndThrow(
  file: File,
  options: {
    maxSize?: number;
    allowedTypes?: Set<string>;
  } = {}
): void {
  const result = validateUploadFile(file, options);
  
  if (!result.valid && result.error) {
    throw new UploadError(
      result.error,
      'invalid_file',
      result.error
    );
  }
}

/**
 * Determine if a file should use chunked upload based on its size
 * 
 * @param file The file to check
 * @param threshold Size threshold in bytes, default 10MB
 * @returns Whether the file should use chunked upload
 */
export function shouldUseChunkedUpload(file: File, threshold = 10 * 1024 * 1024): boolean {
  return file.size > threshold;
}

export default {
  validateUploadFile,
  validateAndThrow,
  shouldUseChunkedUpload,
  MAX_FILE_SIZE,
  ALLOWED_MIME_TYPES,
  UploadError
}; 