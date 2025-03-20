import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface LoadingState {
  isLoading: boolean;
  progress: number;
  stage: 'initial' | 'uploading' | 'analyzing' | 'generating' | 'refining' | 'preview' | 'downloading' | 'formatting' | 'saving' | 'complete' | 'error';
  message: string;
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
  error: null
};

// Create a slice for report generation state
export const reportSlice = createSlice({
  name: 'report',
  initialState,
  reducers: {
    setActiveStep: (state, action: PayloadAction<number>) => {
      state.activeStep = action.payload;
    },
    setReportId: (state, action: PayloadAction<string | null>) => {
      state.reportId = action.payload;
    },
    setLoading: (state, action: PayloadAction<Partial<LoadingState>>) => {
      state.loading = { ...state.loading, ...action.payload };
      // Clear error when we start loading
      if (action.payload.isLoading) {
        state.error = null;
      }
    },
    setDocumentIds: (state, action: PayloadAction<string[]>) => {
      state.documentIds = action.payload;
    },
    addDocumentId: (state, action: PayloadAction<string>) => {
      state.documentIds.push(action.payload);
    },
    setContent: (state, action: PayloadAction<string | null>) => {
      state.content = action.payload;
    },
    setPreviewUrl: (state, action: PayloadAction<string | null>) => {
      state.previewUrl = action.payload;
    },
    setAdditionalInfo: (state, action: PayloadAction<string>) => {
      state.additionalInfo = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      // Reset loading when an error occurs
      if (action.payload) {
        state.loading.isLoading = false;
      }
    },
    resetReport: (state) => {
      return {
        ...initialState,
        documentIds: [] // Reset uploaded documents as well
      };
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
  resetReport
} = reportSlice.actions;

// Export reducer
export default reportSlice.reducer; 