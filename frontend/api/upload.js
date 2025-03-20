import axios from "axios";
import { config } from "../config";
import { handleApiError } from "../utils/errorHandler";

/**
 * Upload multiple files to the backend
 * 
 * @param {File|File[]} files - A single file or array of files to upload
 * @param {number} templateId - Template ID to use for the upload
 * @returns {Promise<Object>} The upload response
 */
export async function uploadFile(files, templateId = 1) {
  const formData = new FormData();
  
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
  
  // Check if total size exceeds 100MB (client-side validation)
  const MAX_SIZE_MB = 100;
  if (totalSize > (MAX_SIZE_MB * 1024 * 1024)) {
    const errorMsg = `Total file size (${totalSizeMB} MB) exceeds the ${MAX_SIZE_MB} MB limit`;
    console.error(errorMsg);
    throw new Error(errorMsg);
  }
  
  // Append each file with the same key 'files'
  filesArray.forEach((file) => {
    formData.append("files", file);
  });
  
  // Make sure template_id is sent as form data
  formData.append("template_id", templateId.toString());
  
  try {
    console.log(`Uploading ${filesArray.length} files to ${config.endpoints.upload}/documents with template ID ${templateId}`);
    
    // Safely log file details if available
    try {
      console.log("Files to upload:", filesArray.map(f => 
        `${f.name || 'unnamed'} (${(f.size / (1024 * 1024)).toFixed(2)} MB, ${f.type || 'unknown type'})`
      ));
    } catch (logError) {
      console.warn("Could not log file details:", logError);
    }
    
    const response = await axios.post(`${config.endpoints.upload}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Accept': 'application/json'
      },
      withCredentials: false, // Set to false when using "*" for allowed origins in the backend
      timeout: 120000 // 120 second timeout for larger files
    });
    
    console.log("Upload response:", response.data);
    return response.data;
  } catch (error) {
    return handleApiError(error, "file upload", { throwError: true });
  }
}

/**
 * Upload a single file to the backend
 * 
 * @param {File} file - The file to upload
 * @param {number} templateId - Template ID to use for the upload
 * @returns {Promise<Object>} The upload response
 */
export async function uploadSingleFile(file, templateId = 1) {
  if (!file) {
    throw new Error("No file provided for upload");
  }
  
  const formData = new FormData();
  formData.append("files", file); // Note the key is 'files' as required by backend
  formData.append("template_id", templateId.toString());
  
  try {
    console.log(`Uploading single file ${file.name} to ${config.endpoints.upload}/documents`);
    
    const response = await axios.post(`${config.endpoints.upload}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000 // 60 second timeout
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
 * @returns {Promise<Object>} The upload response
 */
export async function uploadTemplate(file, name) {
  if (!file) {
    throw new Error("No template file provided for upload");
  }
  
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name || file.name);
  
  try {
    console.log(`Uploading template ${file.name} to ${config.endpoints.upload}/template`);
    
    const response = await axios.post(`${config.endpoints.upload}/template`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000 // 60 second timeout
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