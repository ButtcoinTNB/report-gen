/**
 * API utility functions for communicating with the FastAPI backend
 */

// Configure API URL based on environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchWithErrorHandling(url: string, options: RequestInit = {}) {
  try {
    const response = await fetch(url, options);
    
    // Parse JSON response if possible
    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else if (contentType && contentType.includes('application/pdf')) {
      data = await response.blob();
    } else {
      data = await response.text();
    }
    
    // Handle API error responses
    if (!response.ok) {
      throw new Error(data.detail || data.message || 'An error occurred');
    }
    
    return { data, status: response.status };
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

/**
 * Upload document to the backend
 */
export async function uploadFiles(files: File[]) {
  const formData = new FormData();
  files.forEach((file, index) => {
    formData.append(`files`, file);
  });
  
  // Include template ID (required by the API)
  formData.append('template_id', '1'); // Default template ID, modify as needed
  
  return fetchWithErrorHandling(`${API_BASE_URL}/api/upload/documents`, {
    method: 'POST',
    body: formData,
  });
}

/**
 * Upload a single document
 */
export async function uploadDocument(file: File, reportId?: number, docType: string = 'general') {
  const formData = new FormData();
  formData.append('file', file);
  
  if (reportId) {
    formData.append('report_id', reportId.toString());
  }
  
  formData.append('doc_type', docType);
  
  return fetchWithErrorHandling(`${API_BASE_URL}/api/upload/document`, {
    method: 'POST',
    body: formData,
  });
}

/**
 * Generate report content using uploaded files
 */
export async function generateReport(data: any) {
  return fetchWithErrorHandling(`${API_BASE_URL}/api/generate/generate/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
}

/**
 * Preview the report formatting
 */
export async function previewReport(content: string) {
  return fetchWithErrorHandling(`${API_BASE_URL}/api/format/preview`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ 
      report_content: content 
    }),
  });
}

/**
 * Finalize the report
 */
export async function finalizeReport(data: any) {
  return fetchWithErrorHandling(`${API_BASE_URL}/api/format/final`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
}

/**
 * Update a report
 */
export async function updateReport(reportId: number, updates: { title?: string, content?: string, is_finalized?: boolean }) {
  return fetchWithErrorHandling(`${API_BASE_URL}/api/edit/${reportId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });
}

/**
 * Download a finalized report
 */
export async function downloadReport(reportId: number) {
  return fetchWithErrorHandling(`${API_BASE_URL}/api/download/${reportId}`, {
    method: 'GET',
  });
} 