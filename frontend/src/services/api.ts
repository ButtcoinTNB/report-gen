import axios from 'axios';

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

interface AnalysisResponse {
  extractedVariables: Record<string, string>;
  analysisDetails: Record<string, AnalysisDetails>;
  fieldsNeedingAttention: string[];
}

interface GenerateReportParams {
  documentIds: string[];
  additionalInfo: string;
}

interface ReportPreview {
  previewUrl: string;
  downloadUrl: string;
  reportId: string;
}

export const analyzeDocuments = async (documentIds: string[]): Promise<AnalysisResponse> => {
  try {
    const response = await api.post('/analyze', { document_ids: documentIds });
    if (response.data.status === 'success') {
      return {
        extractedVariables: response.data.extracted_variables,
        analysisDetails: response.data.analysis_details,
        fieldsNeedingAttention: response.data.fields_needing_attention,
      };
    }
    throw new Error(response.data.detail || 'Errore durante l\'analisi dei documenti');
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || 'Errore durante l\'analisi dei documenti');
  }
};

export const generateReport = async ({ documentIds, additionalInfo }: GenerateReportParams): Promise<ReportPreview> => {
  try {
    const response = await api.post('/generate', {
      document_ids: documentIds,
      additional_info: additionalInfo,
    });
    if (response.data.status === 'success') {
      return {
        previewUrl: response.data.preview_url,
        downloadUrl: response.data.download_url,
        reportId: response.data.report_id,
      };
    }
    throw new Error(response.data.detail || 'Errore durante la generazione del report');
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || 'Errore durante la generazione del report');
  }
};

export const refineReport = async (reportId: string, instructions: string): Promise<ReportPreview> => {
  try {
    const response = await api.post(`/reports/${reportId}/refine`, {
      instructions,
    });
    if (response.data.status === 'success') {
      return {
        previewUrl: response.data.preview_url,
        downloadUrl: response.data.download_url,
        reportId: response.data.report_id,
      };
    }
    throw new Error(response.data.detail || 'Errore durante la modifica del report');
  } catch (error: any) {
    throw new Error(error.response?.data?.detail || 'Errore durante la modifica del report');
  }
};

export default api; 