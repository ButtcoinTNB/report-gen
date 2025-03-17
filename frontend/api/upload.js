import axios from "axios";
import { config } from "../config";

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
        'Content-Type': 'multipart/form-data'
      },
      timeout: 120000 // 120 second timeout for larger files
    });
    
    console.log("Upload response:", response.data);
    return response.data;
  } catch (error) {
    console.error("Error during file upload:", error);
    
    let errorMessage = "File upload failed";
    
    if (axios.isAxiosError(error)) {
      if (error.response) {
        // Server responded with an error
        console.error("Server responded with:", error.response.data);
        console.error("Status code:", error.response.status);
        
        if (error.response.data && error.response.data.detail) {
          // Check if it's a file size error
          if (typeof error.response.data.detail === 'string' && 
              error.response.data.detail.includes('size')) {
            errorMessage = `File size error: ${error.response.data.detail}`;
          } else {
            errorMessage = `Server error: ${error.response.data.detail}`;
          }
        } else {
          errorMessage = `Server error (${error.response.status})`;
        }
      } else if (error.request) {
        // Request was made but no response received
        console.error("No response received:", error.request);
        errorMessage = "Server did not respond to upload request. This could be due to the large file size exceeding server limits.";
      } else {
        // Error in setting up the request
        errorMessage = `Request error: ${error.message}`;
      }
    }
    
    throw new Error(errorMessage);
  }
}

// New function for single file uploads - simpler approach
export async function uploadSingleFile(file, templateId = 1) {
  if (!file) {
    throw new Error("No file provided for upload");
  }
  
  const formData = new FormData();
  formData.append("files", file); // Note the key is still 'files' as required by backend
  formData.append("template_id", templateId.toString());
  
  try {
    console.log(`Uploading single file ${file.name} to ${config.endpoints.upload}/documents`);
    
    const response = await axios.post(`${config.endpoints.upload}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000
    });
    
    return response.data;
  } catch (error) {
    console.error("Error during single file upload:", error);
    
    if (axios.isAxiosError(error) && error.response) {
      throw new Error(`Server error (${error.response.status}): ${
        error.response.data?.detail || 'Unknown error'
      }`);
    } else {
      throw new Error("File upload failed: " + (error.message || "Unknown error"));
    }
  }
}

export async function uploadTemplate(file, name) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  
  try {
    console.log(`Uploading template ${file.name} (${file.size} bytes) to ${config.endpoints.upload}/template`);
    
    const response = await axios.post(`${config.endpoints.upload}/template`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000 // 30 second timeout
    });
    
    console.log("Template upload response:", response.data);
    return response.data;
  } catch (error) {
    console.error("Error uploading template:", error);
    
    let errorMessage = "Template upload failed";
    
    if (axios.isAxiosError(error) && error.response) {
      console.error("Server responded with:", error.response.data);
      
      if (error.response.data && error.response.data.detail) {
        errorMessage = `Server error: ${error.response.data.detail}`;
      }
    }
    
    throw new Error(errorMessage);
  }
}

export async function testFileUpload(file) {
  if (!file) {
    throw new Error("No file provided for test upload");
  }
  
  const formData = new FormData();
  formData.append("files", file);  // Change from "file" to "files" to match backend expectation
  
  try {
    console.log(`Testing file upload with ${file.name} (${file.size} bytes) to test-single endpoint`);
    
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
    console.error("Error during test upload:", error);
    
    if (axios.isAxiosError(error) && error.response) {
      console.error("Response data:", error.response.data);
      console.error("Response status:", error.response.status);
      throw new Error(`Server error (${error.response.status}): ${
        JSON.stringify(error.response.data) || 'Unknown error'
      }`);
    } else {
      throw new Error("Test upload failed: " + (error.message || "Unknown error"));
    }
  }
}

export async function testDebugUpload(file) {
  if (!file) {
    throw new Error("No file provided for debug upload");
  }
  
  const formData = new FormData();
  formData.append("files", file);
  formData.append("test_field", "test_value");
  
  try {
    console.log(`Sending file ${file.name} (${file.size} bytes) to debug endpoint`);
    
    const response = await axios.post(`${config.endpoints.upload}/debug-upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000
    });
    
    console.log("Debug upload response:", response.data);
    return response.data;
  } catch (error) {
    console.error("Error during debug upload:", error);
    
    if (axios.isAxiosError(error) && error.response) {
      console.error("Response data:", error.response.data);
      console.error("Response status:", error.response.status);
      throw new Error(`Debug error (${error.response.status}): ${
        JSON.stringify(error.response.data) || 'Unknown error'
      }`);
    } else {
      throw new Error("Debug upload failed: " + (error.message || "Unknown error"));
    }
  }
} 