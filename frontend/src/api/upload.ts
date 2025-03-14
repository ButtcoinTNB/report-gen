import axios from "axios";

export async function uploadFile(file: File, templateId: number = 1) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("template_id", templateId.toString());
  
  const response = await axios.post("http://localhost:8000/api/upload/documents", formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  
  return response.data;
}

export async function uploadTemplate(file: File, name: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  
  const response = await axios.post("http://localhost:8000/api/upload/template", formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  
  return response.data;
}