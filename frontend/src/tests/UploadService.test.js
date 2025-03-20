/**
 * @jest-environment jsdom
 */

import axios from 'axios';
import { UploadService, CHUNKED_UPLOAD_SIZE_THRESHOLD } from '../services/api/UploadService';

// Mock axios
jest.mock('axios');

describe('UploadService', () => {
  // Setup and teardown
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Helper to create a mock file
  function createMockFile(name = 'test.pdf', size = 1024, type = 'application/pdf') {
    const file = new File([''], name, { type });
    Object.defineProperty(file, 'size', { value: size });
    return file;
  }

  describe('isLargeFile', () => {
    it('should identify files larger than the threshold as large files', () => {
      const uploadService = new UploadService();
      const smallFile = createMockFile('small.pdf', CHUNKED_UPLOAD_SIZE_THRESHOLD - 1);
      const largeFile = createMockFile('large.pdf', CHUNKED_UPLOAD_SIZE_THRESHOLD + 1);
      
      expect(uploadService.isLargeFile(smallFile)).toBe(false);
      expect(uploadService.isLargeFile(largeFile)).toBe(true);
    });
  });

  describe('createReport', () => {
    it('should create a report successfully', async () => {
      const mockResponse = {
        data: {
          report_id: 'mock-report-id',
          status: 'success',
          message: 'Report created successfully'
        }
      };
      
      axios.post.mockResolvedValueOnce(mockResponse);
      
      const uploadService = new UploadService();
      const result = await uploadService.createReport();
      
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining('/reports/create'),
        expect.any(Object),
        expect.any(Object)
      );
      expect(result).toHaveProperty('reportId', 'mock-report-id');
    });
  });

  describe('uploadFiles', () => {
    it('should handle a mix of large and small files', async () => {
      // Mock successful responses
      const mockReportResponse = {
        data: {
          report_id: 'mock-report-id',
          status: 'success'
        }
      };
      
      const mockUploadResponse = {
        data: {
          file_id: 'mock-file-id',
          status: 'success'
        }
      };
      
      const mockInitResponse = {
        data: {
          status: 'success',
          data: {
            uploadId: 'mock-upload-id',
            status: 'initialized',
            chunksReceived: 0,
            totalChunks: 2
          }
        }
      };
      
      const mockChunkResponse = {
        data: {
          status: 'success',
          data: {
            uploadId: 'mock-upload-id',
            chunkIndex: 0,
            received: 1,
            total: 2,
            status: 'in_progress'
          }
        }
      };
      
      const mockCompleteResponse = {
        data: {
          status: 'success',
          data: {
            fileId: 'mock-file-id',
            filename: 'large.pdf',
            filePath: '/path/to/file',
            fileSize: CHUNKED_UPLOAD_SIZE_THRESHOLD + 1,
            mimeType: 'application/pdf'
          }
        }
      };
      
      // Set up axios mock responses
      axios.post
        .mockResolvedValueOnce(mockReportResponse) // createReport
        .mockResolvedValueOnce(mockUploadResponse) // uploadFile (small)
        .mockResolvedValueOnce(mockInitResponse)   // init chunked upload
        .mockResolvedValueOnce(mockChunkResponse)  // upload chunk 0
        .mockResolvedValueOnce(mockChunkResponse)  // upload chunk 1
        .mockResolvedValueOnce(mockCompleteResponse); // complete chunked upload
      
      // Create mock files
      const smallFile = createMockFile('small.pdf', 1024);
      const largeFile = createMockFile('large.pdf', CHUNKED_UPLOAD_SIZE_THRESHOLD + 1);
      const files = [smallFile, largeFile];
      
      // Mock Blob and FileReader for chunked upload
      global.Blob = class Blob {
        constructor() {
          return {};
        }
      };
      
      global.FileReader = class FileReader {
        constructor() {
          this.readAsArrayBuffer = jest.fn(() => {
            setTimeout(() => {
              this.onload({ target: { result: new ArrayBuffer(8) } });
            }, 0);
          });
        }
      };
      
      // Call uploadFiles
      const uploadService = new UploadService();
      const mockProgressCallback = jest.fn();
      
      const result = await uploadService.uploadFiles(files, mockProgressCallback);
      
      // Verify correct methods were called
      expect(axios.post).toHaveBeenCalledTimes(6);
      
      // Verify progress callback was called
      expect(mockProgressCallback).toHaveBeenCalled();
      
      // Verify result
      expect(result).toHaveProperty('reportId', 'mock-report-id');
      expect(result).toHaveProperty('status', 'success');
      expect(result).toHaveProperty('fileCount', 2);
    });
  });

  describe('uploadLargeFile', () => {
    it('should handle chunked upload for large files', async () => {
      // Mock successful responses
      const mockInitResponse = {
        data: {
          status: 'success',
          data: {
            uploadId: 'mock-upload-id',
            status: 'initialized',
            chunksReceived: 0,
            totalChunks: 2
          }
        }
      };
      
      const mockChunkResponse = {
        data: {
          status: 'success',
          data: {
            uploadId: 'mock-upload-id',
            chunkIndex: 0,
            received: 1,
            total: 2,
            status: 'in_progress'
          }
        }
      };
      
      const mockCompleteResponse = {
        data: {
          status: 'success',
          data: {
            fileId: 'mock-file-id',
            filename: 'large.pdf',
            filePath: '/path/to/file',
            fileSize: CHUNKED_UPLOAD_SIZE_THRESHOLD + 1,
            mimeType: 'application/pdf',
            reportId: 'mock-report-id'
          }
        }
      };
      
      // Set up axios mock responses
      axios.post
        .mockResolvedValueOnce(mockInitResponse)   // init chunked upload
        .mockResolvedValueOnce(mockChunkResponse)  // upload chunk 0
        .mockResolvedValueOnce(mockChunkResponse)  // upload chunk 1
        .mockResolvedValueOnce(mockCompleteResponse); // complete chunked upload
      
      // Create mock file
      const largeFile = createMockFile('large.pdf', CHUNKED_UPLOAD_SIZE_THRESHOLD + 1);
      
      // Mock Blob and FileReader for chunked upload
      global.Blob = class Blob {
        constructor() {
          return {};
        }
      };
      
      global.FileReader = class FileReader {
        constructor() {
          this.readAsArrayBuffer = jest.fn(() => {
            setTimeout(() => {
              this.onload({ target: { result: new ArrayBuffer(8) } });
            }, 0);
          });
        }
      };
      
      // Call uploadLargeFile
      const uploadService = new UploadService();
      const mockProgressCallback = jest.fn();
      
      const result = await uploadService.uploadLargeFile({
        file: largeFile,
        reportId: 'mock-report-id',
        onProgress: mockProgressCallback
      });
      
      // Verify correct methods were called
      expect(axios.post).toHaveBeenCalledTimes(4);
      
      // Verify initialization call
      expect(axios.post).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('/upload/chunked/init'),
        expect.objectContaining({
          file_name: 'large.pdf',
          file_size: CHUNKED_UPLOAD_SIZE_THRESHOLD + 1,
          mime_type: 'application/pdf'
        }),
        expect.any(Object)
      );
      
      // Verify chunk upload calls
      expect(axios.post).toHaveBeenNthCalledWith(
        2,
        expect.stringMatching(/\/upload\/chunked\/chunk\/mock-upload-id\/0/),
        expect.any(Object),
        expect.any(Object)
      );
      
      // Verify completion call
      expect(axios.post).toHaveBeenNthCalledWith(
        4,
        expect.stringContaining('/upload/chunked/complete'),
        expect.objectContaining({
          upload_id: 'mock-upload-id'
        }),
        expect.any(Object)
      );
      
      // Verify progress callback was called
      expect(mockProgressCallback).toHaveBeenCalled();
      
      // Verify result
      expect(result).toHaveProperty('data.fileId', 'mock-file-id');
      expect(result).toHaveProperty('data.filename', 'large.pdf');
    });
    
    it('should retry on failed chunk uploads', async () => {
      // Mock responses
      const mockInitResponse = {
        data: {
          status: 'success',
          data: {
            uploadId: 'mock-upload-id',
            status: 'initialized',
            chunksReceived: 0,
            totalChunks: 1
          }
        }
      };
      
      const mockErrorResponse = {
        response: {
          status: 500,
          data: { message: 'Server error' }
        }
      };
      
      const mockChunkResponse = {
        data: {
          status: 'success',
          data: {
            uploadId: 'mock-upload-id',
            chunkIndex: 0,
            received: 1,
            total: 1,
            status: 'complete'
          }
        }
      };
      
      const mockCompleteResponse = {
        data: {
          status: 'success',
          data: {
            fileId: 'mock-file-id',
            filename: 'large.pdf',
            filePath: '/path/to/file',
            fileSize: CHUNKED_UPLOAD_SIZE_THRESHOLD + 1,
            mimeType: 'application/pdf',
            reportId: 'mock-report-id'
          }
        }
      };
      
      // Set up axios mock responses
      axios.post
        .mockResolvedValueOnce(mockInitResponse)   // init chunked upload
        .mockRejectedValueOnce(mockErrorResponse)  // upload chunk 0 (fails)
        .mockResolvedValueOnce(mockChunkResponse)  // upload chunk 0 (retry succeeds)
        .mockResolvedValueOnce(mockCompleteResponse); // complete chunked upload
      
      // Create mock file
      const largeFile = createMockFile('large.pdf', CHUNKED_UPLOAD_SIZE_THRESHOLD + 1);
      
      // Mock Blob and FileReader
      global.Blob = class Blob {
        constructor() {
          return {};
        }
      };
      
      global.FileReader = class FileReader {
        constructor() {
          this.readAsArrayBuffer = jest.fn(() => {
            setTimeout(() => {
              this.onload({ target: { result: new ArrayBuffer(8) } });
            }, 0);
          });
        }
      };
      
      // Mock setTimeout for retry delay
      jest.useFakeTimers();
      
      // Call uploadLargeFile
      const uploadService = new UploadService();
      const mockProgressCallback = jest.fn();
      const mockRetryCallback = jest.fn();
      
      const resultPromise = uploadService.uploadLargeFile({
        file: largeFile,
        reportId: 'mock-report-id',
        onProgress: mockProgressCallback,
        onRetry: mockRetryCallback
      });
      
      // Fast-forward through the retry delay
      jest.runAllTimers();
      
      const result = await resultPromise;
      
      // Verify retry callback was called
      expect(mockRetryCallback).toHaveBeenCalledWith(1, 3);
      
      // Verify correct methods were called
      expect(axios.post).toHaveBeenCalledTimes(4);
      
      // Verify result
      expect(result).toHaveProperty('data.fileId', 'mock-file-id');
    });
  });
}); 