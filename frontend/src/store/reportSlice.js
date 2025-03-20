import { createSlice } from '@reduxjs/toolkit';

// Initial state for the report generation process
const initialState = {
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
    setActiveStep: (state, action) => {
      state.activeStep = action.payload;
    },
    setReportId: (state, action) => {
      state.reportId = action.payload;
    },
    setLoading: (state, action) => {
      state.loading = { ...state.loading, ...action.payload };
      // Clear error when we start loading
      if (action.payload.isLoading) {
        state.error = null;
      }
    },
    setDocumentIds: (state, action) => {
      state.documentIds = action.payload;
    },
    addDocumentId: (state, action) => {
      state.documentIds.push(action.payload);
    },
    setContent: (state, action) => {
      state.content = action.payload;
    },
    setPreviewUrl: (state, action) => {
      state.previewUrl = action.payload;
    },
    setAdditionalInfo: (state, action) => {
      state.additionalInfo = action.payload;
    },
    setError: (state, action) => {
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