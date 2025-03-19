export interface Report {
    report_id: string;  // UUID
    title?: string;
    content?: string;
    file_path?: string;
    is_finalized: boolean;
    files_cleaned: boolean;
    template_id?: string;  // UUID
    user_id?: string;  // UUID
    created_at?: string;
    updated_at?: string;
}

export interface ReportPreview {
    previewUrl: string;
    downloadUrl: string;
    reportId: string;  // UUID
    content?: string;
}

export interface AnalysisResponse {
    extractedVariables: Record<string, string>;
    analysisDetails: Record<string, AnalysisDetails>;
    fieldsNeedingAttention: string[];
}

export interface AnalysisDetails {
    confidence: number;
    source: string;
    value: string;
}

export interface File {
    file_id: string;  // UUID
    report_id: string;  // UUID
    filename: string;
    file_path: string;
    file_type: string;
    content?: string;
    file_size: number;
    mime_type?: string;
    user_id?: string;  // UUID
    created_at?: string;
    updated_at?: string;
}

export interface Template {
    template_id: string;  // UUID
    name: string;
    content: string;
    version: string;
    file_path?: string;
    meta_data?: Record<string, any>;
    user_id?: string;  // UUID
    created_at?: string;
    updated_at?: string;
} 