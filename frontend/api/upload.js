import axios from "axios";
import { config } from "../config";
import { handleApiError } from "../utils/errorHandler";
import { 
  createRequestConfig,
  withRetry,
  createApiClient
} from "../utils/corsHelper";

// Create an API client for upload endpoints with extended timeouts for large files
const uploadApi = createApiClient('upload', {
  retries: 3,
  retryDelay: 2000,
  timeout: 300000 // 5 minute timeout for large files
});

// Default chunk size: 5MB
const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024;
// Threshold to use chunked upload: 50MB
const CHUNKED_UPLOAD_THRESHOLD = 50 * 1024 * 1024;
// Maximum size for all files (1GB)
const MAX_UPLOAD_SIZE = 1024 * 1024 * 1024;

/**
 * @typedef {Object} ProgressEvent
 * @property {number} progress - Upload progress as a percentage (0-100)
 * @property {string} stage - Current upload stage (e.g., 'analyzing', 'uploading')
 * @property {string} message - Message describing the current operation
 */

/**
 * @typedef {Object} UploadResponse
 * @property {string} report_id - The ID of the report created or updated
 * @property {string} message - Success message
 * @property {number} file_count - Number of files uploaded
 * @property {string} status - Status of upload
 */

/**
 * Checks if a file is large enough to require chunked uploading
 * 
 * @param {File} file - The file to check
 * @param {number} threshold - Size threshold in bytes (default: 50MB)
 * @returns {boolean} True if the file should be uploaded in chunks
 */
function shouldUseChunkedUpload(file, threshold = CHUNKED_UPLOAD_THRESHOLD) {
  return file.size > threshold;
}

/**
 * Upload a large file in chunks to avoid browser limitations and timeouts
 * 
 * @param {File} file - The file to upload in chunks
 * @param {Object} options - Upload options
 * @param {string} options.reportId - The report ID to associate with the chunks
 * @param {number} options.chunkSize - Size of each chunk in bytes (default: 5MB)
 * @param {Function} options.onProgress - Callback for progress updates
 * @param {number} options.maxRetries - Maximum number of retry attempts per chunk
 * @returns {Promise<Object>} The complete upload response
 */
export async function uploadLargeFile(file, {
  reportId,
  chunkSize = DEFAULT_CHUNK_SIZE,
  onProgress = null,
  maxRetries = 3
} = {}) {
  if (!file) {
    throw new Error("No file provided for chunked upload");
  }
  
  // Calculate total number of chunks
  const totalChunks = Math.ceil(file.size / chunkSize);
  console.log(`Uploading large file ${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB) in ${totalChunks} chunks`);
  
  // Initialize upload
  try {
    if (onProgress) {
      onProgress({
        progress: 0,
        stage: 'uploading',
        message: `Inizializzazione upload di ${file.name}...`
      });
    }
    
    // 1. Start chunked upload - tell the server we're about to send chunks
    const initResponse = await uploadApi.post('/init-chunked-upload', {
      filename: file.name,
      fileSize: file.size,
      fileType: file.type,
      totalChunks: totalChunks,
      reportId: reportId
    });
    
    if (!initResponse.data || !initResponse.data.uploadId) {
      throw new Error("Failed to initialize chunked upload");
    }
    
    const uploadId = initResponse.data.uploadId;
    // If the server created a new report ID, use that
    if (initResponse.data.reportId) {
      reportId = initResponse.data.reportId;
    }
    
    console.log(`Chunked upload initialized with ID: ${uploadId}, report ID: ${reportId}`);
    
    if (onProgress) {
      onProgress({
        progress: 5,
        stage: 'uploading',
        message: `Avvio caricamento a blocchi per ${file.name}...`
      });
    }
    
    // 2. Upload each chunk with retry logic
    let uploadedChunks = 0;
    let uploadedBytes = 0;
    
    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      const start = chunkIndex * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      const chunk = file.slice(start, end);
      
      const formData = new FormData();
      formData.append('chunk', chunk);
      formData.append('chunkIndex', chunkIndex.toString());
      formData.append('uploadId', uploadId);
      
      // Upload chunk with retry
      let chunkUploaded = false;
      let attempts = 0;
      
      while (!chunkUploaded && attempts < maxRetries) {
        try {
          attempts++;
          const chunkResponse = await uploadApi.post('/upload-chunk', formData, {
            isMultipart: true,
            timeout: 60000,
            retryOptions: { maxRetries: 0 } // We're handling retries manually per chunk
          });
          
          if (chunkResponse.data && chunkResponse.data.success) {
            chunkUploaded = true;
            uploadedChunks++;
            uploadedBytes += chunk.size;
            
            // Report overall progress
            if (onProgress) {
              // Progress from 5% to 90% during chunks
              const chunkProgress = Math.round((uploadedChunks / totalChunks) * 85);
              onProgress({
                progress: 5 + chunkProgress,
                stage: 'uploading',
                message: `Caricamento blocco ${chunkIndex + 1}/${totalChunks} di ${file.name}...`
              });
            }
          } else {
            throw new Error(`Chunk upload failed: ${chunkResponse.data?.error || 'Unknown error'}`);
          }
        } catch (error) {
          console.error(`Error uploading chunk ${chunkIndex + 1}/${totalChunks}, attempt ${attempts}/${maxRetries}:`, error);
          
          if (attempts >= maxRetries) {
            throw new Error(`Failed to upload chunk ${chunkIndex + 1} after ${maxRetries} attempts`);
          }
          
          // Wait before retrying (with exponential backoff)
          const retryDelay = 1000 * Math.pow(2, attempts - 1);
          await new Promise(resolve => setTimeout(resolve, retryDelay));
          
          if (onProgress) {
            onProgress({
              progress: 5 + Math.round((uploadedChunks / totalChunks) * 85),
              stage: 'retrying',
              message: `Riprovo il caricamento del blocco ${chunkIndex + 1}/${totalChunks}...`,
              attempt: attempts,
              maxAttempts: maxRetries
            });
          }
        }
      }
    }
    
    if (onProgress) {
      onProgress({
        progress: 90,
        stage: 'uploading',
        message: `Finalizzazione caricamento di ${file.name}...`
      });
    }
    
    // 3. Complete the chunked upload
    const completeResponse = await uploadApi.post('/complete-chunked-upload', {
      uploadId: uploadId
    });
    
    if (onProgress) {
      onProgress({
        progress: 100,
        stage: 'completed',
        message: `Caricamento di ${file.name} completato!`
      });
    }
    
    return completeResponse.data;
  } catch (error) {
    console.error("Chunked upload failed:", error);
    return handleApiError(error, "chunked file upload", { throwError: true });
  }
}

/**
 * Upload multiple files to the backend, using chunked uploads for large files
 * 
 * @param {File|File[]} files - A single file or array of files to upload
 * @param {string} reportId - Optional report ID to associate with the files
 * @param {Function} onProgress - Optional callback for upload progress
 * @returns {Promise<Object>} The upload response
 */
export async function uploadFile(files, reportId = null, onProgress = null) {
  // Validate files parameter
  if (!files) {
    console.error("No files provided to uploadFile function");
    throw new Error("No files were provided for upload");
  }
  
  // Convert single file to array if needed
  const filesArray = Array.isArray(files) ? files : [files];
  
  if (filesArray.length === 0) {
    console.error("Empty files array provided to uploadFile function");
    throw new Error("No files were provided for upload");
  }
  
  // Calculate total size before uploading
  let totalSize = 0;
  for (const file of filesArray) {
    totalSize += file.size || 0;
  }
  const totalSizeMB = (totalSize / (1024 * 1024)).toFixed(2);
  console.log(`Total size of all files: ${totalSizeMB} MB`);
  
  // Check if we have any large files that need chunked upload
  const largeFiles = filesArray.filter(file => shouldUseChunkedUpload(file));
  const regularFiles = filesArray.filter(file => !shouldUseChunkedUpload(file));
  
  console.log(`Found ${largeFiles.length} large files and ${regularFiles.length} regular files`);
  
  try {
    // Client-side total size check before uploading anything
    if (totalSize > MAX_UPLOAD_SIZE) {
      const errorMsg = `Total file size (${totalSizeMB} MB) exceeds the 1GB limit`;
      console.error(errorMsg);
      throw new Error(errorMsg);
    }
    
    // Step 1: If we don't have a report ID yet, create one
    if (!reportId && filesArray.length > 0) {
      try {
        if (onProgress) {
          onProgress({
            progress: 0,
            stage: 'uploading',
            message: 'Creazione nuovo report...'
          });
        }
        
        const createResponse = await uploadApi.post('/reports');
        reportId = createResponse.data.report_id;
        console.log(`Created new report with ID: ${reportId}`);
      } catch (error) {
        console.error("Error creating report:", error);
        throw new Error(`Failed to create report: ${error.message}`);
      }
    }
    
    // Step 2: Upload large files first using chunked uploads (one by one)
    if (largeFiles.length > 0) {
      // Calculate how much progress to allocate to large files vs regular files
      const largeFilesProgressWeight = largeFiles.length / filesArray.length;
      let currentLargeFileIndex = 0;
      
      for (const largeFile of largeFiles) {
        const thisFileProgressOffset = (currentLargeFileIndex / largeFiles.length) * largeFilesProgressWeight * 100;
        const thisFileProgressWeight = (1 / largeFiles.length) * largeFilesProgressWeight;
        
        await uploadLargeFile(largeFile, {
          reportId,
          onProgress: (progressEvent) => {
            if (onProgress) {
              // Scale this file's progress to its portion of the overall progress
              const scaledProgress = thisFileProgressOffset + 
                (progressEvent.progress * thisFileProgressWeight);
              
              onProgress({
                progress: Math.round(scaledProgress),
                stage: progressEvent.stage || 'uploading',
                message: progressEvent.message || `Caricamento ${currentLargeFileIndex + 1}/${largeFiles.length}: ${largeFile.name}`
              });
            }
          }
        });
        
        currentLargeFileIndex++;
      }
    }
    
    // Step 3: Upload regular files (all at once)
    if (regularFiles.length > 0) {
      // Calculate progress starting point after large files
      const regularFilesProgressOffset = largeFiles.length > 0 ? 
        (largeFiles.length / filesArray.length) * 100 : 0;
      
      if (onProgress) {
        onProgress({
          progress: Math.round(regularFilesProgressOffset),
          stage: 'uploading',
          message: `Caricamento di ${regularFiles.length} file standard...`
        });
      }
      
      const formData = new FormData();
      regularFiles.forEach(file => {
        formData.append("files", file);
      });
      
      // Add the report ID 
      if (reportId) {
        formData.append("report_id", reportId);
      }
      
      const regularResponse = await uploadApi.post('/documents', formData, {
        isMultipart: true,
        timeout: 120000, // 2 minute timeout
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            // Scale regular files progress to remaining portion
            const regularProgress = (progressEvent.loaded / progressEvent.total) * 
              ((regularFiles.length / filesArray.length) * 100);
            
            onProgress({
              progress: Math.round(regularFilesProgressOffset + regularProgress),
              stage: 'uploading',
              message: `Caricamento file standard: ${Math.round((progressEvent.loaded * 100) / progressEvent.total)}%`
            });
          }
        },
        retryOptions: {
          maxRetries: 2,
          retryDelay: 2000
        }
      });
      
      // If this is the first upload, get the report ID
      if (!reportId && regularResponse.data && regularResponse.data.report_id) {
        reportId = regularResponse.data.report_id;
      }
    }
    
    if (onProgress) {
      onProgress({
        progress: 100,
        stage: 'completed',
        message: 'Tutti i file caricati con successo!'
      });
    }
    
    // Return a standard response with the report ID
    return {
      report_id: reportId,
      message: 'Caricamento completato con successo',
      file_count: filesArray.length,
      status: 'success'
    };
  } catch (error) {
    console.error("File upload failed:", error);
    return handleApiError(error, "file upload", { throwError: true });
  }
}

/**
 * Upload a single file to the backend
 * 
 * @param {File} file - The file to upload
 * @param {number} templateId - Template ID to use for the upload
 * @param {Function} onProgress - Optional callback for upload progress
 * @returns {Promise<Object>} The upload response
 */
export async function uploadSingleFile(file, templateId = 1, onProgress = null) {
  // Check if we should use chunked upload based on file size
  if (shouldUseChunkedUpload(file)) {
    console.log(`File ${file.name} is large (${(file.size / (1024 * 1024)).toFixed(2)} MB), using chunked upload`);
    return uploadLargeFile(file, { 
      templateId, 
      onProgress
    });
  }

  if (!file) {
    throw new Error("No file provided for upload");
  }
  
  const formData = new FormData();
  formData.append("files", file); // Note the key is 'files' as required by backend
  formData.append("template_id", templateId.toString());
  
  try {
    console.log(`Uploading single file ${file.name} to ${config.endpoints.upload}/documents`);
    
    // Use our uploadApi client with retry functionality
    const response = await uploadApi.post('/documents', formData, {
      isMultipart: true,
      timeout: 60000, // 60 second timeout
      onUploadProgress: onProgress,
      retryOptions: {
        maxRetries: 2
      }
    });
    
    return response.data;
  } catch (error) {
    return handleApiError(error, "single file upload");
  }
}

/**
 * Upload a template file to the backend
 * 
 * @param {File} file - The template file to upload
 * @param {string} name - Name of the template
 * @param {Function} onProgress - Optional callback for upload progress
 * @returns {Promise<Object>} The upload response
 */
export async function uploadTemplate(file, name, onProgress = null) {
  if (!file) {
    throw new Error("No template file provided for upload");
  }
  
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name || file.name);
  
  try {
    console.log(`Uploading template ${file.name} to ${config.endpoints.upload}/template`);
    
    // Use our uploadApi client with retry functionality
    const response = await uploadApi.post('/template', formData, {
      isMultipart: true,
      timeout: 60000, // 60 second timeout
      onUploadProgress: onProgress,
      retryOptions: {
        maxRetries: 2
      }
    });
    
    return response.data;
  } catch (error) {
    return handleApiError(error, "template upload");
  }
}

/**
 * Test file upload to various endpoints for debugging
 * 
 * @param {File} file - The file to test upload
 * @returns {Promise<Object>} Test response data
 */
export async function testFileUpload(file) {
  if (!file) {
    throw new Error("No file provided for test upload");
  }
  
  const formData = new FormData();
  formData.append("files", file);  // Using "files" to match backend expectation
  
  try {
    console.log(`Testing file upload with ${file.name} to test-single endpoint`);
    
    // First try the test-single endpoint
    const testResponse = await axios.post(`${config.endpoints.upload}/test-single`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000
    });
    
    console.log("Test single upload response:", testResponse.data);
    
    // Try the full documents endpoint with the same file
    console.log("Now trying the main documents endpoint...");
    formData.append("template_id", "1");  // Add template_id for the documents endpoint
    
    const mainResponse = await axios.post(`${config.endpoints.upload}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000
    });
    
    console.log("Main documents endpoint response:", mainResponse.data);
    
    return {
      testResponse: testResponse.data,
      mainResponse: mainResponse.data
    };
  } catch (error) {
    return handleApiError(error, "test upload");
  }
}

/**
 * Send a file to a debug upload endpoint for testing
 * 
 * @param {File} file - The file to debug upload
 * @returns {Promise<Object>} Debug response data
 */
export async function testDebugUpload(file) {
  if (!file) {
    throw new Error("No file provided for debug upload");
  }
  
  const formData = new FormData();
  formData.append("files", file);
  formData.append("test_field", "test_value");
  
  try {
    console.log(`Sending file ${file.name} to debug endpoint`);
    
    const response = await axios.post(`${config.endpoints.upload}/debug-upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000
    });
    
    console.log("Debug upload response:", response.data);
    return response.data;
  } catch (error) {
    return handleApiError(error, "debug upload");
  }
}

/**
 * Upload a DOCX template file
 * 
 * @param {File} file - The DOCX template file to upload
 * @returns {Promise<Object>} Upload response
 */
export async function uploadDocxTemplate(file) {
  if (!file) {
    throw new Error("No DOCX template file provided");
  }
  
  const formData = new FormData();
  formData.append("file", file);
  
  try {
    console.log(`Uploading DOCX template ${file.name} to ${config.endpoints.upload}/template/docx`);
    
    const response = await axios.post(`${config.endpoints.upload}/template/docx`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000
    });
    
    console.log("DOCX template upload response:", response.data);
    return response.data;
  } catch (error) {
    return handleApiError(error, "DOCX template upload");
  }
} 