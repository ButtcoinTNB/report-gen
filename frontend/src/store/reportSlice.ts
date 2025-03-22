import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ErrorCategory } from '../utils/errorHandler';

export interface LoadingState {
  isLoading: boolean;
  progress: number;
  stage: 'initial' | 'uploading' | 'analyzing' | 'generating' | 'refining' | 'preview' | 'downloading' | 'formatting' | 'saving' | 'complete' | 'error';
  message: string;
}

export interface ErrorDetails {
  category?: ErrorCategory;
  userGuidance?: string;
  technicalDetails?: string;
  retryable?: boolean;
}

export interface BackgroundUploadState {
  isUploading: boolean;
  totalFiles: number;
  uploadedFiles: number;
  progress: number;
  error: string | null;
  errorDetails?: ErrorDetails;
  shouldCleanup?: boolean;
  cleanupReportId?: string;
  uploadStartTime?: number;
  uploadSessionId?: string;
}

export interface AgentLoopState {
  taskId: string | null;
  isInitializing: boolean;
  isRunning: boolean;
  progress: number;
  stage: 'idle' | 'initializing' | 'writing' | 'reviewing' | 'complete' | 'error';
  currentIteration: number;
  totalIterations: number;
  message: string;
  error: string | null;
  canCancel: boolean;
  estimatedTimeRemaining: number | null;
  startTime: number | null;
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
  agentLoop: AgentLoopState;
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
  agentLoop: {
    taskId: null,
    isInitializing: false,
    isRunning: false,
    progress: 0,
    stage: 'idle',
    currentIteration: 0,
    totalIterations: 3, // Default to 3 iterations
    message: '',
    error: null,
    canCancel: false,
    estimatedTimeRemaining: null,
    startTime: null
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
    initAgentLoop: (state, action: PayloadAction<{ taskId?: string }>) => {
      // Initialize the agent loop state
      const taskId = action.payload.taskId || crypto.randomUUID?.() || `task-${Date.now()}`;
      state.agentLoop = {
        ...state.agentLoop,
        taskId,
        isInitializing: true,
        isRunning: false,
        progress: 0,
        stage: 'initializing',
        message: 'Inizializzazione in corso...',
        error: null,
        canCancel: true,
        startTime: Date.now()
      };
      state.lastActivityTime = Date.now();
    },
    updateAgentLoopProgress: (state, action: PayloadAction<{ 
      progress: number; 
      message: string; 
      stage?: AgentLoopState['stage'];
      estimatedTimeRemaining?: number | null;
    }>) => {
      const { progress, message, stage, estimatedTimeRemaining } = action.payload;
      
      // If the agent loop is initializing and progress >= 20, transition to running
      const isRunning = progress >= 20 || state.agentLoop.isRunning;
      const isInitializing = progress < 20 && state.agentLoop.isInitializing;
      
      // Determine the appropriate stage
      const newStage = stage || (
        isInitializing ? 'initializing' : 
        progress >= 100 ? 'complete' : 
        isRunning ? (state.agentLoop.stage === 'writing' ? 'reviewing' : 'writing') : 
        state.agentLoop.stage
      );
      
      // Update the state
      state.agentLoop = {
        ...state.agentLoop,
        isInitializing,
        isRunning,
        progress,
        stage: newStage,
        message,
        estimatedTimeRemaining: estimatedTimeRemaining ?? state.agentLoop.estimatedTimeRemaining
      };
      
      // For writing or reviewing stages, update the current iteration
      if (newStage === 'writing' && state.agentLoop.stage !== 'writing') {
        // Starting a new iteration when transitioning to writing
        state.agentLoop.currentIteration = Math.min(
          state.agentLoop.currentIteration + 1, 
          state.agentLoop.totalIterations
        );
      }
      
      state.lastActivityTime = Date.now();
    },
    completeAgentLoop: (state, action: PayloadAction<{
      content?: string;
      previewUrl?: string;
      iterations?: number;
    }>) => {
      const { content, previewUrl, iterations } = action.payload;
      
      // Update report content if provided
      if (content) {
        state.content = content;
      }
      
      // Update preview URL if provided
      if (previewUrl) {
        state.previewUrl = previewUrl;
      }
      
      // Update agent loop state
      state.agentLoop = {
        ...state.agentLoop,
        isInitializing: false,
        isRunning: false,
        progress: 100,
        stage: 'complete',
        message: 'Generazione completata con successo',
        error: null,
        canCancel: false,
        currentIteration: iterations || state.agentLoop.currentIteration,
        totalIterations: iterations || state.agentLoop.totalIterations
      };
      
      state.lastActivityTime = Date.now();
    },
    failAgentLoop: (state, action: PayloadAction<string>) => {
      state.agentLoop = {
        ...state.agentLoop,
        isInitializing: false,
        isRunning: false,
        stage: 'error',
        message: 'Si è verificato un errore durante la generazione del report',
        error: action.payload,
        canCancel: false,
      };
      state.error = action.payload;
      state.lastActivityTime = Date.now();
    },
    cancelAgentLoop: (state) => {
      // Mark the agent loop as cancelled without losing the task ID
      const taskId = state.agentLoop.taskId;
      state.agentLoop = {
        ...initialState.agentLoop,
        taskId,
        message: 'Generazione annullata dall\'utente',
        stage: 'idle'
      };
      state.lastActivityTime = Date.now();
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
    resetAgentLoop: (state) => {
      // Reset just the agent loop portion
      state.agentLoop = initialState.agentLoop;
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
        
        // If agent loop is running, mark it for cancellation
        if (state.agentLoop.isRunning || state.agentLoop.isInitializing) {
          // The middleware will handle the actual API call for cancellation
          state.agentLoop.canCancel = false;
          state.agentLoop.message = 'Sessione scaduta, generazione annullata';
          state.agentLoop.stage = 'error';
          state.agentLoop.error = 'La sessione è scaduta per inattività';
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
  initAgentLoop,
  updateAgentLoopProgress,
  completeAgentLoop,
  failAgentLoop,
  cancelAgentLoop,
  resetState,
  resetUpload,
  resetAgentLoop,
  setSessionTimeout,
  updateLastActivityTime,
  checkSessionTimeout,
} = reportSlice.actions;

// Export reducer
export default reportSlice.reducer; 