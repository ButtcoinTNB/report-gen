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
    const response = await axios.post(`${config.endpoints.upload}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    
    console.log("Upload response:", response.data);
    return response.data;
  } catch (error) {
    console.error("Error during file upload:", error);
    if (axios.isAxiosError(error) && error.response) {
      console.error("Server responded with:", error.response.data);
    }
    throw error;
  }
}

export async function uploadTemplate(file, name) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  
  const response = await axios.post(`${config.endpoints.upload}/template`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  
  return response.data;
} 