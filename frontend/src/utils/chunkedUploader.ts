/**
 * Chunked file uploader utility for handling large file uploads with resume capability
 */

import axios, { AxiosProgressEvent, AxiosRequestConfig, AxiosError } from 'axios';
import config from '@/config';
import { createError, handleError, ErrorCategory, ErrorSeverity } from './errorHandler';
import { validateAndThrow, UploadError } from './uploadValidator';

// Constants
const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024; // 5MB default chunk size
const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAY_MS = 1000;
const API_BASE_URL = config.API_URL;
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

// Type definitions
export interface ChunkedUploadConfig {
  file: File;
  reportId?: string;
  chunkSize?: number;
  onProgress?: (progress: number) => void;
  onError?: (error: Error) => void;
  onComplete?: (result: ChunkedUploadResult) => void;
  onChunkComplete?: (chunkIndex: number, totalChunks: number) => void;
  abortSignal?: AbortSignal;
}

export interface ChunkedUploadResult {
  success: boolean;
  fileId: string;
  reportId: string;
  filename: string;
  size: number;
  mimeType: string;
  path: string;
  url: string;
}

export interface UploadMetadata {
  uploadId: string;
  chunkSize: number;
  totalChunks: number;
  uploadedChunks: number[];
  resumable: boolean;
}

/**
 * Class for managing chunked file uploads
 */
export class ChunkedUploader {
  private file: File;
  private reportId?: string;
  private chunkSize: number;
  private onProgress?: (progress: number) => void;
  private onError?: (error: Error) => void;
  private onComplete?: (result: ChunkedUploadResult) => void;
  private onChunkComplete?: (chunkIndex: number, totalChunks: number) => void;
  private abortSignal?: AbortSignal;
  private canceled = false;
  private metadata?: UploadMetadata;
  private uploadId?: string;
  
  /**
   * Constructor
   */
  constructor(config: ChunkedUploadConfig) {
    this.file = config.file;
    this.reportId = config.reportId;
    this.chunkSize = config.chunkSize || DEFAULT_CHUNK_SIZE;
    this.onProgress = config.onProgress;
    this.onError = config.onError;
    this.onComplete = config.onComplete;
    this.onChunkComplete = config.onChunkComplete;
    this.abortSignal = config.abortSignal;
    
    // If an abort signal is provided, set up a listener
    if (this.abortSignal) {
      this.abortSignal.addEventListener('abort', () => {
        this.canceled = true;
        this.cancelUpload();
      });
    }
  }
  
  /**
   * Start the upload process
   */
  public async start(): Promise<ChunkedUploadResult | null> {
    try {
      // Validate file before uploading
      validateAndThrow(this.file);
      
      // Initialize the upload
      await this.initialize();
      
      if (this.canceled) return null;
      
      // Upload all chunks
      await this.uploadChunks();
      
      if (this.canceled) return null;
      
      // Finalize the upload
      const result = await this.finalize();
      
      if (this.onComplete) {
        this.onComplete(result);
      }
      
      return result;
    } catch (error) {
      await this.handleError(error);
      return null;
    }
  }
  
  /**
   * Cancel the upload
   */
  public async cancelUpload(): Promise<void> {
    this.canceled = true;
    
    if (this.uploadId) {
      try {
        const formData = new FormData();
        formData.append('uploadId', this.uploadId);
        
        await axios.post(
          `${API_BASE_URL}/api/uploads/cancel`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          }
        );
      } catch (error) {
        console.error('Error canceling upload:', error);
        // Don't throw error on cancel failure - it's a best effort operation
      }
    }
  }
  
  /**
   * Handle errors during upload
   */
  private async handleError(error: unknown): Promise<void> {
    if (this.canceled) {
      if (this.onError) {
        this.onError(new UploadError('Upload was canceled', 'upload_canceled'));
      }
      return;
    }
    
    // Try to cancel the upload on the server if an error occurs
    if (this.uploadId) {
      try {
        await this.cancelUpload();
      } catch (cancelError) {
        console.error('Failed to cancel upload after error:', cancelError);
      }
    }
    
    // Handle different error types
    let uploadError: Error;
    
    if (error instanceof UploadError) {
      uploadError = error;
    } else if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<any>;
      const statusCode = axiosError.response?.status || 0;
      const errorData = axiosError.response?.data as any;
      
      let message = 'Upload failed';
      let code = 'network_error';
      let details = axiosError.message;
      let retry = statusCode >= 500 || statusCode === 429 || !statusCode;
      
      if (errorData && typeof errorData === 'object') {
        message = errorData.message || message;
        code = errorData.code || code;
        details = errorData.detail || details;
      }
      
      uploadError = new UploadError(message, code, details, retry);
    } else {
      uploadError = new UploadError(
        'Upload failed',
        'unknown_error',
        error instanceof Error ? error.message : String(error)
      );
    }
    
    // Use the app's error handler
    handleError(uploadError, {
      uploadId: this.uploadId,
      fileName: this.file.name,
      fileSize: this.file.size,
      fileType: this.file.type
    });
    
    // Call the error callback if provided
    if (this.onError) {
      this.onError(uploadError);
    }
    
    // Re-throw the error for upstream handling
    throw uploadError;
  }
  
  /**
   * Initialize the upload process
   */
  private async initialize(): Promise<void> {
    const formData = new FormData();
    formData.append('filename', this.file.name);
    formData.append('fileSize', this.file.size.toString());
    formData.append('mimeType', this.file.type);
    
    if (this.reportId) {
      formData.append('reportId', this.reportId);
    }
    
    try {
      const response = await axios.post<UploadMetadata>(
        `${API_BASE_URL}/api/uploads/initialize`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      
      this.metadata = response.data;
      this.uploadId = response.data.uploadId;
      this.chunkSize = response.data.chunkSize;
    } catch (error) {
      console.error('Error initializing upload:', error);
      await this.handleError(error);
    }
  }
  
  /**
   * Upload all chunks
   */
  private async uploadChunks(): Promise<void> {
    if (!this.metadata || !this.uploadId) {
      throw new UploadError('Upload not initialized', 'not_initialized');
    }
    
    const totalChunks = this.metadata.totalChunks;
    const uploadedChunks = new Set(this.metadata.uploadedChunks);
    
    // Loop through all chunks and upload them
    for (let i = 0; i < totalChunks; i++) {
      if (this.canceled) return;
      
      // Skip chunks that have already been uploaded
      if (uploadedChunks.has(i)) {
        if (this.onProgress) {
          const progress = ((uploadedChunks.size) / totalChunks) * 100;
          this.onProgress(progress);
        }
        continue;
      }
      
      // Upload the chunk
      let retryCount = 0;
      let success = false;
      
      while (retryCount < MAX_RETRY_ATTEMPTS && !success && !this.canceled) {
        try {
          await this.uploadChunk(i);
          success = true;
          uploadedChunks.add(i);
          
          if (this.onChunkComplete) {
            this.onChunkComplete(i, totalChunks);
          }
          
          if (this.onProgress) {
            const progress = ((uploadedChunks.size) / totalChunks) * 100;
            this.onProgress(progress);
          }
        } catch (error) {
          retryCount++;
          
          // Check if the error is retryable
          const isRetryable = 
            axios.isAxiosError(error) && 
            (error.response?.status === undefined || 
             error.response.status >= 500 || 
             error.response.status === 429);
          
          if (!isRetryable || retryCount >= MAX_RETRY_ATTEMPTS) {
            await this.handleError(error);
            return; // handleError will throw, but just in case
          }
          
          // Calculate backoff time with exponential backoff
          const backoffTime = RETRY_DELAY_MS * Math.pow(2, retryCount - 1);
          console.warn(`Retrying chunk ${i} upload. Attempt ${retryCount} of ${MAX_RETRY_ATTEMPTS}. Waiting ${backoffTime}ms...`);
          
          // Wait before retrying with exponential backoff
          await new Promise(resolve => setTimeout(resolve, backoffTime));
        }
      }
    }
  }
  
  /**
   * Upload a single chunk
   */
  private async uploadChunk(chunkIndex: number): Promise<void> {
    if (!this.metadata || !this.uploadId) {
      throw new UploadError('Upload not initialized', 'not_initialized');
    }
    
    const start = chunkIndex * this.chunkSize;
    const end = Math.min(start + this.chunkSize, this.file.size);
    const chunk = this.file.slice(start, end);
    
    const formData = new FormData();
    formData.append('uploadId', this.uploadId);
    formData.append('chunkIndex', chunkIndex.toString());
    formData.append('start', start.toString());
    formData.append('end', end.toString());
    formData.append('chunk', chunk);
    
    try {
      await axios.post(
        `${API_BASE_URL}/api/uploads/chunk`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 60000, // 60 second timeout for chunk uploads
        }
      );
    } catch (error) {
      console.error(`Error uploading chunk ${chunkIndex}:`, error);
      throw error; // Let the retry mechanism handle it
    }
  }
  
  /**
   * Finalize the upload
   */
  private async finalize(): Promise<ChunkedUploadResult> {
    if (!this.metadata || !this.uploadId) {
      throw new UploadError('Upload not initialized', 'not_initialized');
    }
    
    const formData = new FormData();
    formData.append('uploadId', this.uploadId);
    formData.append('filename', this.file.name);
    
    if (this.reportId) {
      formData.append('reportId', this.reportId);
    }
    
    try {
      const response = await axios.post<ChunkedUploadResult>(
        `${API_BASE_URL}/api/uploads/finalize`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 120000, // 2-minute timeout for finalization
        }
      );
      
      return response.data;
    } catch (error) {
      console.error('Error finalizing upload:', error);
      await this.handleError(error);
      throw error; // handleError should already throw, but just for type safety
    }
  }
}

/**
 * Utility function to upload a file using chunked upload
 */
export async function uploadFileChunked(config: ChunkedUploadConfig): Promise<ChunkedUploadResult | null> {
  const uploader = new ChunkedUploader(config);
  return await uploader.start();
}

/**
 * Determine if a file should use chunked upload based on its size
 */
export function shouldUseChunkedUpload(file: File, threshold = 10 * 1024 * 1024): boolean {
  return file.size > threshold;
}

/**
 * Validate if a file can be uploaded (size and type checks)
 */
export function validateUploadFile(file: File): { valid: boolean; error?: string } {
  if (file.size <= 0) {
    return { valid: false, error: 'File is empty' };
  }
  
  if (file.size > MAX_FILE_SIZE) {
    return { valid: false, error: `Maximum file size is ${MAX_FILE_SIZE / (1024 * 1024)}MB` };
  }
  
  if (!ALLOWED_MIME_TYPES.has(file.type)) {
    return { valid: false, error: `File type ${file.type || 'unknown'} is not allowed` };
  }
  
  return { valid: true };
}

export default {
  ChunkedUploader,
  uploadFileChunked,
  shouldUseChunkedUpload,
  validateUploadFile
}; 