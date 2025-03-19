import axios from 'axios';
import { Report, ReportPreview, AnalysisResponse } from '../types';

// Create axios instance with default config
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
  // Set longer timeouts for large file uploads
  timeout: 600000, // 10 minutes
  maxContentLength: 1073741824, // 1GB
  maxBodyLength: 1073741824, // 1GB
});

interface AnalysisDetails {
  valore: string;
  confidenza: 'ALTA' | 'MEDIA' | 'BASSA';
  richiede_verifica: boolean;
}

interface GenerateRequest {
    reportId: string;  // UUID
    documentIds: string[];  // UUIDs
    additionalInfo?: string;
    templateId?: string;  // UUID
}

interface RefineRequest {
    reportId: string;  // UUID
    instructions: string;
}

interface ProgressUpdate {
    step: number;
    message: string;
    progress: number;
}

interface ReportResponse {
    content: string;
    error?: boolean;
}

export const analyzeDocuments = async (documentIds: string[]): Promise<AnalysisResponse> => {
    const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ documentIds })
    });
    
    if (!response.ok) {
        throw new Error('Failed to analyze documents');
    }
    
    return response.json();
};

export const generateReport = async (
    request: GenerateRequest,
    options = {},
    onProgress?: (update: ProgressUpdate) => void
): Promise<ReportResponse> => {
    const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        throw new Error('Failed to generate report');
    }

    const result = await response.json();
    return result;
};

export const refineReport = async (reportId: string, instructions: string): Promise<ReportPreview> => {
    const response = await fetch(`/api/reports/${reportId}/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instructions })
    });
    
    if (!response.ok) {
        throw new Error('Failed to refine report');
    }
    
    return response.json();
};

export const downloadReport = async (reportId: string): Promise<Blob> => {
    const response = await fetch(`/api/download/${reportId}`);
    
    if (!response.ok) {
        throw new Error('Failed to download report');
    }
    
    return response.blob();
};

export default api; 