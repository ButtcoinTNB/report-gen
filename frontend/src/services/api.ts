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
    report_id: string;  // UUID (renamed from reportId to match backend)
    document_ids: string[];  // UUIDs (renamed from documentIds to match backend)
    additional_info?: string;
    template_id?: string;  // UUID (renamed from templateId to match backend)
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
    // Convert property names to snake_case if they aren't already
    const payload = {
        report_id: request.report_id,
        document_ids: request.document_ids,
        additional_info: request.additional_info,
        template_id: request.template_id
    };
    
    const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
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