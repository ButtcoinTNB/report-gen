import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface LoadingState {
  isLoading: boolean;
  progress: number;
  stage: 'initial' | 'uploading' | 'analyzing' | 'generating' | 'refining' | 'preview' | 'downloading' | 'formatting' | 'saving' | 'complete' | 'error';
  message: string;
}

export interface BackgroundUploadState {
  isUploading: boolean;
  totalFiles: number;
  uploadedFiles: number;
  progress: number;
  error: string | null;
  shouldCleanup?: boolean;
  cleanupReportId?: string;
  uploadStartTime?: number;
  uploadSessionId?: string;
}

export interface ReportState {
  activeStep: number;
  reportId: string | null;
  loading: LoadingState;
  documentIds: string[];
  content: string | null;
  previewUrl: string | null;
  additionalInfo: string;
  error: string | null;
  backgroundUpload: BackgroundUploadState;
  sessionTimeout: number; // Session timeout in minutes
  lastActivityTime: number; // Last user activity timestamp
}

// Initial state for the report generation process
const initialState: ReportState = {
  activeStep: 0,
  reportId: null,
  loading: {
    isLoading: false,
    progress: 0,
    stage: 'initial',
    message: ''
  },
  documentIds: [],
  content: null,
  previewUrl: null,
  additionalInfo: '',
  error: null,
  backgroundUpload: {
    isUploading: false,
    totalFiles: 0,
    uploadedFiles: 0,
    progress: 0,
    error: null,
    uploadStartTime: Date.now(),
    uploadSessionId: crypto.randomUUID?.() || `session-${Date.now()}`
  },
  sessionTimeout: 30, // 30 minutes session timeout by default
  lastActivityTime: Date.now(),
};

// Create a slice for report generation state
export const reportSlice = createSlice({
  name: 'report',
  initialState,
  reducers: {
    setActiveStep: (state, action: PayloadAction<number>) => {
      state.activeStep = action.payload;
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setReportId: (state, action: PayloadAction<string>) => {
      state.reportId = action.payload;
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setLoading: (state, action: PayloadAction<Partial<LoadingState>>) => {
      state.loading = { ...state.loading, ...action.payload };
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setDocumentIds: (state, action: PayloadAction<string[]>) => {
      state.documentIds = action.payload;
      state.lastActivityTime = Date.now(); // Update activity time
    },
    addDocumentId: (state, action: PayloadAction<string>) => {
      state.documentIds.push(action.payload);
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setContent: (state, action: PayloadAction<string>) => {
      state.content = action.payload;
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setPreviewUrl: (state, action: PayloadAction<string>) => {
      state.previewUrl = action.payload;
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setAdditionalInfo: (state, action: PayloadAction<string>) => {
      state.additionalInfo = action.payload;
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setBackgroundUpload: (state, action: PayloadAction<Partial<BackgroundUploadState>>) => {
      // If it's a complete fresh start of upload, set a new session ID
      if (action.payload.isUploading === true && 
          action.payload.progress === 0 && 
          action.payload.totalFiles && 
          action.payload.totalFiles > 0) {
        state.backgroundUpload = {
          ...state.backgroundUpload,
          ...action.payload,
          uploadStartTime: Date.now(),
          uploadSessionId: crypto.randomUUID?.() || `session-${Date.now()}`
        };
      } else {
        // Otherwise just update existing state
        state.backgroundUpload = { ...state.backgroundUpload, ...action.payload };
      }
      
      // If we explicitly set shouldCleanup, trigger API cleanup via middleware
      if (action.payload.shouldCleanup) {
        // The middleware will handle the actual cleanup API call
        console.log(`Cleanup requested for report: ${action.payload.cleanupReportId || state.reportId}`);
      }
      
      state.lastActivityTime = Date.now(); // Update activity time
    },
    resetState: (state) => {
      // Reset to initial state but preserve session timeout settings
      const sessionTimeout = state.sessionTimeout;
      Object.assign(state, initialState);
      state.sessionTimeout = sessionTimeout;
      state.lastActivityTime = Date.now();
    },
    resetUpload: (state) => {
      // Reset just the upload portion
      state.backgroundUpload = initialState.backgroundUpload;
      state.lastActivityTime = Date.now();
    },
    setSessionTimeout: (state, action: PayloadAction<number>) => {
      state.sessionTimeout = action.payload;
    },
    updateLastActivityTime: (state) => {
      state.lastActivityTime = Date.now();
    },
    checkSessionTimeout: (state) => {
      const currentTime = Date.now();
      const timeoutMs = state.sessionTimeout * 60 * 1000; // Convert minutes to milliseconds
      
      // If session has timed out, clean up
      if (currentTime - state.lastActivityTime > timeoutMs) {
        // First check if there are uploads in progress
        if (state.backgroundUpload.isUploading) {
          // Set shouldCleanup flag to true to trigger cleanup middleware
          state.backgroundUpload.shouldCleanup = true;
          state.backgroundUpload.cleanupReportId = state.reportId || undefined;
        }
        
        // Reset state
        Object.assign(state, initialState);
        state.lastActivityTime = currentTime;
      }
    }
  }
});

// Export actions
export const { 
  setActiveStep, 
  setReportId, 
  setLoading, 
  setDocumentIds,
  addDocumentId,
  setContent,
  setPreviewUrl,
  setAdditionalInfo,
  setError,
  setBackgroundUpload,
  resetState,
  resetUpload,
  setSessionTimeout,
  updateLastActivityTime,
  checkSessionTimeout,
} = reportSlice.actions;

// Export reducer
export default reportSlice.reducer; 