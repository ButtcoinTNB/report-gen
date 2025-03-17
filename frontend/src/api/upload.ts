import axios, { AxiosError } from "axios";

// Get API URL from environment or fallback to localhost
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function uploadFile(file: File, templateId: number = 1) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("template_id", templateId.toString());
  
  const response = await axios.post(`${API_URL}/api/upload/documents`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  
  return response.data;
}

export async function uploadSingleFile(file: File, templateId: number = 1) {
  if (!file) {
    throw new Error("No file provided for upload");
  }
  
  const formData = new FormData();
  formData.append("files", file); // Note the key is 'files' as required by backend
  formData.append("template_id", templateId.toString());
  
  try {
    console.log(`Uploading single file ${file.name} to ${API_URL}/api/upload/documents`);
    
    const response = await axios.post(`${API_URL}/api/upload/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000
    });
    
    return response.data;
  } catch (error: unknown) {
    console.error("Error during single file upload:", error);
    
    if (axios.isAxiosError(error) && error.response) {
      throw new Error(`Server error (${error.response.status}): ${
        error.response.data?.detail || 'Unknown error'
      }`);
    } else {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error("File upload failed: " + errorMessage);
    }
  }
}

export async function uploadTemplate(file: File, name: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  
  const response = await axios.post(`${API_URL}/api/upload/template`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  
  return response.data;
}

export async function testFileUpload(file: File) {
  if (!file) {
    throw new Error("No file provided for test upload");
  }
  
  const formData = new FormData();
  formData.append("files", file);  // Using "files" to match backend expectation
  
  try {
    console.log(`Testing file upload with ${file.name} to test-single endpoint`);
    
    // First try the test-single endpoint
    const testResponse = await axios.post(`${API_URL}/api/upload/test-single`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000
    });
    
    console.log("Test single upload response:", testResponse.data);
    
    // Try the full documents endpoint with the same file
    console.log("Now trying the main documents endpoint...");
    formData.append("template_id", "1");  // Add template_id for the documents endpoint
    
    const mainResponse = await axios.post(`${API_URL}/api/upload/documents`, formData, {
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
  } catch (error: unknown) {
    console.error("Error during test upload:", error);
    
    if (axios.isAxiosError(error) && error.response) {
      console.error("Response data:", error.response.data);
      console.error("Response status:", error.response.status);
      throw new Error(`Server error (${error.response.status}): ${
        JSON.stringify(error.response.data) || 'Unknown error'
      }`);
    } else {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error("Test upload failed: " + errorMessage);
    }
  }
}

export async function testDebugUpload(file: File) {
  if (!file) {
    throw new Error("No file provided for debug upload");
  }
  
  const formData = new FormData();
  formData.append("files", file);
  formData.append("test_field", "test_value");
  
  try {
    console.log(`Sending file ${file.name} to debug endpoint`);
    
    const response = await axios.post(`${API_URL}/api/upload/debug-upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000
    });
    
    console.log("Debug upload response:", response.data);
    return response.data;
  } catch (error: unknown) {
    console.error("Error during debug upload:", error);
    
    if (axios.isAxiosError(error) && error.response) {
      console.error("Response data:", error.response.data);
      console.error("Response status:", error.response.status);
      throw new Error(`Debug error (${error.response.status}): ${
        JSON.stringify(error.response.data) || 'Unknown error'
      }`);
    } else {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error("Debug upload failed: " + errorMessage);
    }
  }
}

export async function uploadDocxTemplate(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  
  try {
    console.log(`Uploading DOCX template ${file.name} to ${API_URL}/api/upload/template/docx`);
    
    const response = await axios.post(`${API_URL}/api/upload/template/docx`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 30000
    });
    
    console.log("DOCX template upload response:", response.data);
    return response.data;
  } catch (error: unknown) {
    console.error("Error uploading DOCX template:", error);
    
    if (axios.isAxiosError(error) && error.response) {
      console.error("Server responded with:", error.response.data);
      
      if (error.response.data && error.response.data.detail) {
        throw new Error(`Server error: ${error.response.data.detail}`);
      }
    }
    
    throw new Error("DOCX template upload failed");
  }
}