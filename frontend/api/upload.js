import axios from "axios";
import { config } from "../config";

export async function uploadFile(files, templateId = 1) {
  const formData = new FormData();
  
  // Append each file with the same key 'files'
  files.forEach((file) => {
    formData.append("files", file);
  });
  
  // Make sure template_id is sent as form data
  formData.append("template_id", templateId.toString());
  
  try {
    console.log(`Uploading ${files.length} files to ${config.endpoints.upload}/documents with template ID ${templateId}`);
    console.log("Files to upload:", files.map(f => `${f.name} (${f.size} bytes, ${f.type})`));
    
    const response = await axios.post(`${config.endpoints.upload}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000 // 60 second timeout for larger files
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
          errorMessage = `Server error: ${error.response.data.detail}`;
        } else {
          errorMessage = `Server error (${error.response.status})`;
        }
      } else if (error.request) {
        // Request was made but no response received
        console.error("No response received:", error.request);
        errorMessage = "Server did not respond to upload request";
      } else {
        // Error in setting up the request
        errorMessage = `Request error: ${error.message}`;
      }
    }
    
    throw new Error(errorMessage);
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