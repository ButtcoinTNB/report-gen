import { ApiClient, ApiRequestOptions, createApiClient } from './ApiClient';
import { config } from '../../../config';
import { logger } from '../../utils/logger';
import { adaptApiRequest, adaptApiResponse } from '../../utils/adapters';

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
  upload_id: string;
  message: string;
  status: 'success' | 'error';
  chunk_size: number;
}

/**
 * Response for a chunk upload
 */
export interface ChunkUploadResponse {
  status: 'success' | 'error';
  message: string;
  upload_id: string;
  chunk_index: number;
}

/**
 * Response for a completed chunked upload
 */
export interface CompletedUploadResponse {
  status: 'success' | 'error';
  message: string;
  upload_id: string;
  file_id: string;
  file_name: string;
  file_size: number;
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
export const CHUNKED_UPLOAD_SIZE_THRESHOLD = 50 * 1024 * 1024; // 50 MB
// Default chunk size for chunked uploads
export const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024; // 5 MB

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ChunkedUploadInitResponseCamel {
  uploadId: string;
  message: string;
  status: 'success' | 'error';
  chunkSize: number;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface ChunkUploadResponseCamel {
  status: 'success' | 'error';
  message: string;
  uploadId: string;
  chunkIndex: number;
}

/**
 * Frontend-friendly version with camelCase properties
 */
export interface CompletedUploadResponseCamel {
  status: 'success' | 'error';
  message: string;
  uploadId: string;
  fileId: string;
  fileName: string;
  fileSize: number;
}

/**
 * Service for handling file uploads with support for large files via chunking
 */
export class UploadService extends ApiClient {
  /**
   * Create a new Upload Service
   */
  constructor() {
    // Get the base URL for the upload API
    let baseUrl: string;
    
    if (config.endpoints?.upload) {
      baseUrl = config.endpoints.upload;
    } else {
      baseUrl = `${config.API_URL}/api/upload`;
    }
    
    super({
      baseUrl,
      defaultTimeout: 300000, // 5 minutes
      defaultRetries: 3,
      defaultRetryDelay: 2000,
    });
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
      const formData = new FormData();
      formData.append('files', file);
      
      // Use adaptApiRequest for reportId
      if (reportId) {
        const snakeCaseRequest = adaptApiRequest({ reportId });
        formData.append('report_id', snakeCaseRequest.report_id);
      }

      const response = await this.post<ReportResponse>('/documents', formData, {
        isMultipart: true,
        onUploadProgress: event => {
          if (onProgress && event.total) {
            const progress = Math.round((event.loaded * 100) / event.total);
            onProgress(progress);
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
      throw error;
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
      
      // If we only have small files, use the standard upload
      if (largeFiles.length === 0) {
        const formData = new FormData();
        
        for (const file of files) {
          formData.append('files', file);
        }
        
        const response = await this.post<ReportResponse>('/documents', formData, {
          isMultipart: true,
          onUploadProgress: event => {
            if (onProgress && event.total) {
              const progress = Math.round((event.loaded * 100) / event.total);
              onProgress(progress);
            }
          },
          retryOptions: {
            maxRetries: 3,
            retryDelay: 2000
          }
        });
        
        // Convert response to camelCase
        return adaptApiResponse<ReportResponseCamel>(response.data);
      }
      
      // If we have large files, we need to handle them differently
      // 1. Create a report first
      const reportId = await this.createReport();
      
      // 2. Upload each large file using chunked upload
      let completedFiles = 0;
      const totalFiles = files.length;
      
      // Calculate weights for progress tracking
      // Large files get more weight in the progress calculation
      const totalSize = files.reduce((sum, file) => sum + file.size, 0);
      const fileWeights = files.map(file => file.size / totalSize);
      
      // Array to track each file's progress
      const fileProgress = new Array(files.length).fill(0);
      
      // Function to update overall progress
      const updateProgress = () => {
        if (onProgress) {
          const weightedProgress = fileProgress.reduce(
            (sum, progress, index) => sum + progress * fileWeights[index], 
            0
          );
          onProgress(Math.floor(weightedProgress));
        }
      };
      
      // 3. Upload large files with chunking
      for (let i = 0; i < largeFiles.length; i++) {
        const file = largeFiles[i];
        const fileIndex = files.indexOf(file);
        
        try {
          await this.uploadLargeFile({
            file,
            reportId,
            onProgress: (progress) => {
              fileProgress[fileIndex] = progress;
              updateProgress();
            }
          });
          
          completedFiles++;
          fileProgress[fileIndex] = 100;
          updateProgress();
        } catch (error) {
          logger.error(`Error uploading large file ${file.name}:`, error);
          throw error;
        }
      }
      
      // 4. Upload small files if any (as a batch)
      if (smallFiles.length > 0) {
        const formData = new FormData();
        
        for (const file of smallFiles) {
          formData.append('files', file);
        }
        
        formData.append('report_id', reportId);
        
        try {
          // Track progress for small files
          const smallFilesStartIndex = files.length - smallFiles.length;
          
          await this.post<ReportResponse>('/documents', formData, {
            isMultipart: true,
            onUploadProgress: event => {
              if (event.total) {
                const progress = Math.round((event.loaded * 100) / event.total);
                // Update progress for all small files
                for (let i = 0; i < smallFiles.length; i++) {
                  const fileIndex = files.indexOf(smallFiles[i]);
                  fileProgress[fileIndex] = progress;
                }
                updateProgress();
              }
            }
          });
          
          // Mark all small files as complete
          for (const file of smallFiles) {
            const fileIndex = files.indexOf(file);
            fileProgress[fileIndex] = 100;
          }
          updateProgress();
          
          completedFiles += smallFiles.length;
        } catch (error) {
          logger.error('Error uploading small files:', error);
          throw error;
        }
      }
      
      // Return a formatted response
      return adaptApiResponse<ReportResponseCamel>({
        report_id: reportId,
        message: `Uploaded ${completedFiles} files successfully`,
        status: 'success',
        file_count: completedFiles
      });
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
        filesize: file.size,
        mimetype: file.type,
        reportId: reportId || null
      });

      const initResponse = await this.post<ChunkedUploadInitResponse>('/init-chunked-upload', initRequest);
      
      // Convert response to camelCase
      const camelInitResponse = adaptApiResponse<ChunkedUploadInitResponseCamel>(initResponse.data);
      
      const { uploadId, chunkSize: responseChunkSize } = camelInitResponse;
      const actualChunkSize = responseChunkSize || chunkSize;
      
      // 2. Calculate number of chunks
      const totalChunks = Math.ceil(file.size / actualChunkSize);
      let uploadedChunks = 0;
      
      // 3. Upload each chunk
      for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        const start = chunkIndex * actualChunkSize;
        const end = Math.min(file.size, start + actualChunkSize);
        const chunk = file.slice(start, end);
        
        const formData = new FormData();
        formData.append('chunk', chunk);
        formData.append('upload_id', uploadId);
        formData.append('chunk_index', chunkIndex.toString());
        
        try {
          // Use retry logic for each chunk
          await this.post<ChunkUploadResponse>('/upload-chunk', formData, {
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
        uploadId,
        filename: file.name,
        totalChunks
      });

      const completeResponse = await this.post<CompletedUploadResponse>('/complete-chunked-upload', completeRequest);
      
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