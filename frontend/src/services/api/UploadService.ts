import { ApiClient, ApiRequestOptions, createApiClient } from './ApiClient';
import { config } from '../../../config';
import { logger } from '../../utils/logger';
import { adaptApiRequest, adaptApiResponse } from '../../utils/adapters';
import { processUploadError } from '../../utils/errorHandler';
import { throttle } from '../../utils/throttle';

/**
 * Response for a report creation or update
 */
export interface ReportResponse {
  report_id: string;
  message: string;
  status: 'success' | 'error';
  file_count?: number;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ReportResponseCamel {
  reportId: string;
  message: string;
  status: 'success' | 'error';
  fileCount?: number;
}

/**
 * Response for a chunked upload initialization
 */
export interface ChunkedUploadInitResponse {
  status: 'success' | 'error';
  data: {
    uploadId: string;
    status: string;
    chunksReceived: number;
    totalChunks: number;
  };
}

/**
 * Response for a chunk upload
 */
export interface ChunkUploadResponse {
  status: 'success' | 'error';
  data: {
    uploadId: string;
    chunkIndex: number;
    received: number;
    total: number;
    status: string;
  };
}

/**
 * Response for a completed chunked upload
 */
export interface CompletedUploadResponse {
  status: 'success' | 'error';
  data: {
    fileId: string;
    filename: string;
    filePath: string;
    fileSize: number;
    mimeType: string;
    reportId?: string;
  };
}

/**
 * Configuration for chunked uploads
 */
export interface ChunkedUploadConfig {
  /** File to upload */
  file: File;
  /** Size of each chunk in bytes */
  chunkSize?: number;
  /** Callback for upload progress */
  onProgress?: (percentage: number) => void;
  /** Callback for upload retries */
  onRetry?: (attempt: number, maxRetries: number) => void;
  /** Report ID to associate with the upload */
  reportId?: string;
}

// The size threshold above which to use chunked uploads
export const CHUNKED_UPLOAD_SIZE_THRESHOLD = 10 * 1024 * 1024; // 10MB
// Default chunk size for chunked uploads
export const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024; // 5 MB

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ChunkedUploadInitResponseCamel {
  status: 'success' | 'error';
  data: {
    uploadId: string;
    status: string;
    chunksReceived: number;
    totalChunks: number;
  };
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ChunkUploadResponseCamel {
  status: 'success' | 'error';
  data: {
    uploadId: string;
    chunkIndex: number;
    received: number;
    total: number;
    status: string;
  };
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface CompletedUploadResponseCamel {
  status: 'success' | 'error';
  data: {
    fileId: string;
    filename: string;
    filePath: string;
    fileSize: number;
    mimeType: string;
    reportId?: string;
  };
}

// Add allowed MIME types constant
const ALLOWED_MIME_TYPES = [
  // Documents
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/rtf',
  'application/vnd.oasis.opendocument.text',
  'text/plain',
  'text/csv',
  'text/markdown',
  'text/html',
  // Spreadsheets
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  // Images
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/bmp',
  'image/webp',
  'image/tiff'
];

/**
 * Service for handling file uploads with support for large files via chunking
 */
export class UploadService extends ApiClient {
  /**
   * Create a new Upload Service
   */
  constructor() {
    // Get the base URL for the upload API - use the Next.js API route
    let baseUrl = '/api/upload';
    
    super({
      baseUrl,
      defaultTimeout: 300000, // 5 minutes
      defaultRetries: 3,
      defaultRetryDelay: 2000,
    });
  }

  /**
   * Validate file type
   * @param file The file to validate
   * @throws Error if file type is not allowed
   */
  private validateFileType(file: File): void {
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      throw new Error(`File type ${file.type} is not allowed. Allowed types: ${ALLOWED_MIME_TYPES.join(', ')}`);
    }
  }

  /**
   * Determine if a file should use chunked uploads based on its size
   * @param file The file to check
   * @returns true if the file should use chunked uploads
   */
  shouldUseChunkedUpload(file: File): boolean {
    return file.size > CHUNKED_UPLOAD_SIZE_THRESHOLD;
  }

  /**
   * Create a new report
   * @returns Promise with the report ID
   */
  async createReport(): Promise<string> {
    try {
      // No request body needed, but we'll use the adapter for consistency
      const request = adaptApiRequest({});
      
      const response = await this.post<ReportResponse>('/reports', request);
      
      // Convert response to camelCase
      const camelResponse = adaptApiResponse<ReportResponseCamel>(response.data);
      
      // Return just the report ID
      return camelResponse.reportId;
    } catch (error) {
      logger.error('Error creating report:', error);
      throw error;
    }
  }

  /**
   * Upload a single file directly (for smaller files)
   * @param file The file to upload
   * @param reportId The report ID to associate with the file
   * @param onProgress Optional progress callback
   * @returns Promise with the upload response in camelCase format
   */
  async uploadSingleFile(
    file: File, 
    reportId?: string, 
    onProgress?: (progress: number) => void
  ): Promise<ReportResponseCamel> {
    try {
      // Validate file type
      this.validateFileType(file);
      
      const formData = new FormData();
      formData.append('files', file);
      
      // Use adaptApiRequest for reportId
      if (reportId) {
        const snakeCaseRequest = adaptApiRequest({ reportId });
        formData.append('report_id', snakeCaseRequest.report_id);
      }

      // Create a throttled version of the progress callback
      const throttledProgress = onProgress ? throttle(onProgress, 250) : undefined;

      const response = await this.post<ReportResponse>('/documents', formData, {
        isMultipart: true,
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
        },
        onUploadProgress: event => {
          if (throttledProgress && event.total) {
            const progress = Math.round((event.loaded * 100) / event.total);
            throttledProgress(progress);
          }
        },
        retryOptions: {
          maxRetries: 3,
          retryDelay: 2000,
          onRetry: (attempt, maxRetries) => {
            logger.info(`Retrying file upload (${attempt}/${maxRetries})...`);
          }
        }
      });
      
      // Convert response to camelCase
      return adaptApiResponse<ReportResponseCamel>(response.data);
    } catch (error) {
      logger.error('Error uploading file:', error);
      // Process error for better user feedback
      const structuredError = processUploadError(error);
      // Preserve the original error's structure but augment with structured info
      const enhancedError = new Error(structuredError.message);
      (enhancedError as any).category = structuredError.category;
      (enhancedError as any).userGuidance = structuredError.userGuidance;
      (enhancedError as any).retryable = structuredError.retryable;
      (enhancedError as any).originalError = error;
      throw enhancedError;
    }
  }

  /**
   * Upload multiple files
   * @param files Array of files to upload
   * @param onProgress Optional progress callback
   * @returns Promise with the upload response in camelCase format
   */
  async uploadFiles(
    files: File[], 
    onProgress?: (progress: number) => void
  ): Promise<ReportResponseCamel> {
    try {
      // First, check if we have any large files that need chunked upload
      const largeFiles = files.filter(file => this.shouldUseChunkedUpload(file));
      const smallFiles = files.filter(file => !this.shouldUseChunkedUpload(file));
      
      // Create a new report ID first
      const reportId = await this.createReport();
      
      // Keep track of overall progress
      let totalProgress = 0;
      
      // Create a throttled progress callback
      const throttledProgress = onProgress ? throttle(onProgress, 250) : undefined;
      
      const updateProgress = (fileProgress: number, fileIndex: number, fileCount: number) => {
        if (!throttledProgress) return;
        
        // Calculate weighted progress for this file
        const fileWeight = 1 / fileCount;
        const weightedProgress = fileProgress * fileWeight;
        
        // Update total progress by adding the weighted progress of the current file
        totalProgress = (fileIndex * fileWeight * 100) + weightedProgress;
        throttledProgress(Math.floor(totalProgress));
      };
      
      // Handle small files first with regular upload
      if (smallFiles.length > 0) {
        const formData = new FormData();
        
        for (const file of smallFiles) {
          formData.append('files', file);
        }
        
        // Add report ID to formData
        formData.append('report_id', reportId);
        
        await this.post<ReportResponse>('/documents', formData, {
          isMultipart: true,
          onUploadProgress: event => {
            if (throttledProgress && event.total) {
              const smallFilesProgress = Math.round((event.loaded * 100) / event.total);
              // If we have large files too, small files are only part of the total progress
              if (largeFiles.length > 0) {
                const smallFilesWeight = smallFiles.length / files.length;
                throttledProgress(Math.floor(smallFilesProgress * smallFilesWeight));
              } else {
                throttledProgress(smallFilesProgress);
              }
            }
          },
          retryOptions: {
            maxRetries: 3,
            retryDelay: 2000
          }
        });
      }
      
      // Handle large files with chunked upload
      if (largeFiles.length > 0) {
        // Upload each large file using chunked upload
        for (let i = 0; i < largeFiles.length; i++) {
          const file = largeFiles[i];
          
          // Calculate file's weight in progress calculation
          const fileStartIndex = smallFiles.length + i;
          const totalFileCount = files.length;
          
          await this.uploadLargeFile({
            file,
            reportId,
            onProgress: (fileProgress) => {
              updateProgress(fileProgress, fileStartIndex, totalFileCount);
            },
            onRetry: (attempt, maxRetries) => {
              logger.info(`Retrying large file upload (${attempt}/${maxRetries})...`);
            }
          });
        }
      }
      
      // Set progress to 100% when all uploads are complete
      if (onProgress) {
        onProgress(100);
      }
      
      // Return the response with the report ID
      return {
        reportId,
        status: 'success',
        message: `Successfully uploaded ${files.length} file(s)`,
        fileCount: files.length
      };
    } catch (error) {
      logger.error('Error uploading files:', error);
      throw error;
    }
  }

  /**
   * Upload a template file
   * @param templateFile The template file to upload
   * @param onProgress Optional progress callback
   * @returns Promise with the upload response in camelCase format
   */
  async uploadTemplate(
    templateFile: File, 
    onProgress?: (progress: number) => void
  ): Promise<ReportResponseCamel> {
    try {
      const formData = new FormData();
      formData.append('file', templateFile);
      
      const response = await this.post<ReportResponse>('/templates', formData, {
        isMultipart: true,
        onUploadProgress: event => {
          if (onProgress && event.total) {
            const progress = Math.round((event.loaded * 100) / event.total);
            onProgress(progress);
          }
        }
      });
      
      // Convert response to camelCase
      return adaptApiResponse<ReportResponseCamel>(response.data);
    } catch (error) {
      logger.error('Error uploading template:', error);
      throw error;
    }
  }

  /**
   * Upload a large file using chunked uploads
   * @param config Configuration for the chunked upload
   * @returns Promise with the completed upload response in camelCase format
   */
  async uploadLargeFile(config: ChunkedUploadConfig): Promise<CompletedUploadResponseCamel> {
    const { file, chunkSize = DEFAULT_CHUNK_SIZE, onProgress, onRetry, reportId } = config;
    
    try {
      // 1. Initialize chunked upload - convert request to snake_case
      const initRequest = adaptApiRequest({
        filename: file.name,
        fileSize: file.size,
        totalChunks: Math.ceil(file.size / chunkSize),
        fileType: file.type,
        reportId: reportId || null
      });

      const initResponse = await this.post<ChunkedUploadInitResponse>('/chunked/init', initRequest);
      
      // Convert response to camelCase
      const camelInitResponse = adaptApiResponse<ChunkedUploadInitResponseCamel>(initResponse.data);
      
      const uploadId = camelInitResponse.data.uploadId;
      
      // 2. Calculate number of chunks
      const totalChunks = Math.ceil(file.size / chunkSize);
      let uploadedChunks = 0;
      
      // 3. Upload each chunk
      for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        const start = chunkIndex * chunkSize;
        const end = Math.min(file.size, start + chunkSize);
        const chunk = file.slice(start, end);
        
        const formData = new FormData();
        formData.append('file', new File([chunk], file.name));
        
        try {
          // Use specific URL pattern for each chunk that matches backend
          const url = `/chunked/chunk/${uploadId}/${chunkIndex}`;
          
          // Use retry logic for each chunk
          await this.post<ChunkUploadResponse>(url, formData, {
            isMultipart: true,
            onUploadProgress: (event) => {
              if (onProgress && event.total) {
                // Calculate progress considering both completed chunks and current chunk progress
                const chunkProgress = event.loaded / event.total;
                const totalProgress = ((uploadedChunks + chunkProgress) / totalChunks) * 100;
                onProgress(Math.floor(totalProgress));
              }
            },
            retryOptions: {
              maxRetries: 3,
              retryDelay: 2000,
              onRetry: (attempt, maxRetries) => {
                logger.info(`Retrying chunk ${chunkIndex} upload (${attempt}/${maxRetries})...`);
                if (onRetry) {
                  onRetry(attempt, maxRetries);
                }
              }
            }
          });
          
          uploadedChunks++;
          
          // Update progress after chunk completion
          if (onProgress) {
            onProgress(Math.floor((uploadedChunks / totalChunks) * 100));
          }
        } catch (error) {
          logger.error(`Error uploading chunk ${chunkIndex}:`, error);
          throw error;
        }
      }
      
      // 4. Complete the chunked upload - convert request to snake_case
      const completeRequest = adaptApiRequest({
        uploadId
      });

      const completeResponse = await this.post<CompletedUploadResponse>('/chunked/complete', completeRequest);
      
      // Convert response to camelCase
      return adaptApiResponse<CompletedUploadResponseCamel>(completeResponse.data);
    } catch (error) {
      logger.error(`Error in chunked upload for ${file.name}:`, error);
      throw error;
    }
  }
}

// Export a singleton instance
export const uploadService = new UploadService(); 