import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ErrorCategory } from '../utils/errorHandler';
import { LoadingState, LoadingStage, ReportState, BackgroundUploadState, AgentLoopState, StateTransaction } from './types';
import { AppThunk } from './index';
import { generateUUID } from '../utils/common';

// Transaction state used to track ongoing state operations
export interface ErrorDetails {
  category?: ErrorCategory;
  userGuidance?: string;
  technicalDetails?: string;
  retryable?: boolean;
}

// Initial state for the report generation process
const initialState: ReportState = {
  activeStep: 0,
  reportId: null,
  content: null,
  previewUrl: null,
  loading: {
    isLoading: false,
    stage: 'initial',
    message: undefined,
    progress: undefined
  },
  documentIds: [],
  additionalInfo: '',
  error: null,
  backgroundUpload: {
    isUploading: false,
    progress: 0,
    error: null,
    totalFiles: 0,
    uploadedFiles: 0,
    uploadStartTime: Date.now(),
    uploadSessionId: generateUUID()
  },
  agentLoop: {
    taskId: null,
    isInitializing: false,
    isRunning: false,
    isStalled: false,
    progress: 0,
    stage: 'idle',
    currentIteration: 0,
    totalIterations: 3,
    message: '',
    error: null,
    canCancel: false,
    estimatedTimeRemaining: null,
    startTime: null,
    transactionId: null,
    stalledSince: null
  },
  sessionTimeout: 30, // 30 minutes default
  lastActivityTime: Date.now(),
  pendingTransactions: []
};

// Generate unique transaction ID
const generateTransactionId = (): string => {
  return `txn-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// Default stall detection threshold (30 seconds)
const DEFAULT_STALL_THRESHOLD = 30000;

// Create a slice for report generation state
export const reportSlice = createSlice({
  name: 'report',
  initialState,
  reducers: {
    setActiveStep: (state, action: PayloadAction<number>) => {
      state.activeStep = action.payload;
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setReportId: (state, action: PayloadAction<string | null>) => {
      state.reportId = action.payload;
      state.lastActivityTime = Date.now();
    },
    setLoading: (state, action: PayloadAction<LoadingState>) => {
      state.loading = action.payload;
      state.lastActivityTime = Date.now();
    },
    setDocumentIds: (state, action: PayloadAction<string[]>) => {
      state.documentIds = action.payload;
      state.lastActivityTime = Date.now(); // Update activity time
    },
    addDocumentId: (state, action: PayloadAction<string>) => {
      state.documentIds.push(action.payload);
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setContent: (state, action: PayloadAction<string | null>) => {
      state.content = action.payload;
      state.lastActivityTime = Date.now();
    },
    setPreviewUrl: (state, action: PayloadAction<string | null>) => {
      state.previewUrl = action.payload;
      state.lastActivityTime = Date.now();
    },
    setAdditionalInfo: (state, action: PayloadAction<string>) => {
      state.additionalInfo = action.payload;
      state.lastActivityTime = Date.now(); // Update activity time
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      state.lastActivityTime = Date.now();
    },
    setBackgroundUpload: (state, action: PayloadAction<Partial<BackgroundUploadState>>) => {
      state.backgroundUpload = { ...state.backgroundUpload, ...action.payload };
      state.lastActivityTime = Date.now();
    },
    setAgentLoop: (state, action: PayloadAction<Partial<AgentLoopState>>) => {
      state.agentLoop = { ...state.agentLoop, ...action.payload };
      state.lastActivityTime = Date.now();
    },
    addTransaction: (state, action: PayloadAction<StateTransaction>) => {
      state.pendingTransactions.push({
        ...action.payload,
        isPending: true,
        startTime: Date.now()
      });
      state.lastActivityTime = Date.now();
    },
    updateTransaction: (state, action: PayloadAction<{ id: string; updates: Partial<StateTransaction> }>) => {
      const transaction = state.pendingTransactions.find(t => t.id === action.payload.id);
      if (transaction) {
        Object.assign(transaction, action.payload.updates);
      }
      state.lastActivityTime = Date.now();
    },
    resetReport: (state) => {
      state.reportId = null;
      state.content = null;
      state.previewUrl = null;
      state.loading = initialState.loading;
      state.error = null;
      state.documentIds = [];
      state.additionalInfo = '';
      state.backgroundUpload = initialState.backgroundUpload;
      state.agentLoop = initialState.agentLoop;
      state.pendingTransactions = [];
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
    },
    beginTransaction: (state, action: PayloadAction<Omit<StateTransaction, 'id' | 'startTime' | 'isPending'>>) => {
      const transactionId = generateTransactionId();
      const transaction: StateTransaction = {
        ...action.payload,
        id: transactionId,
        startTime: Date.now(),
        isPending: true
      };
      
      state.pendingTransactions.push(transaction);
      
      if (action.payload.taskId && action.payload.operation === 'cancel') {
        // Mark the agent loop state as being in a transaction
        if (state.agentLoop.taskId === action.payload.taskId) {
          state.agentLoop.transactionId = transactionId;
        }
      }
      
      state.lastActivityTime = Date.now();
    },
    completeTransaction: (state, action: PayloadAction<{ transactionId: string; success: boolean }>) => {
      const { transactionId, success } = action.payload;
      const transactionIndex = state.pendingTransactions.findIndex(t => t.id === transactionId);
      
      if (transactionIndex >= 0) {
        if (success) {
          // Remove the completed transaction
          state.pendingTransactions.splice(transactionIndex, 1);
        } else {
          // Mark transaction as not pending but keep for retry/logging
          state.pendingTransactions[transactionIndex].isPending = false;
        }
      }
      
      // Clear transaction ID from agent loop if it matches
      if (state.agentLoop.transactionId === transactionId) {
        state.agentLoop.transactionId = null;
      }
      
      state.lastActivityTime = Date.now();
    },
    cleanupStaleTransactions: (state) => {
      // Clean up stale transactions older than 5 minutes
      const now = Date.now();
      const fiveMinutesAgo = now - (5 * 60 * 1000);
      
      state.pendingTransactions = state.pendingTransactions.filter(transaction => {
        return transaction.isPending || transaction.startTime > fiveMinutesAgo;
      });
      
      // Clear transaction ID if it's no longer in the transactions list
      if (state.agentLoop.transactionId) {
        const transactionExists = state.pendingTransactions.some(
          t => t.id === state.agentLoop.transactionId
        );
        
        if (!transactionExists) {
          state.agentLoop.transactionId = null;
        }
      }
    },
    detectStalledAgentLoop: (state, action: PayloadAction<{ threshold?: number } | undefined>) => {
      // Use provided threshold or default if not provided
      const threshold = action.payload?.threshold || DEFAULT_STALL_THRESHOLD;
      const now = Date.now();
      
      // Only check for stalled processes if the agent loop is active
      if ((state.agentLoop.isInitializing || state.agentLoop.isRunning) && 
          !state.agentLoop.isStalled) {
        
        // Calculate time since last update
        const timeSinceLastActivity = now - state.lastActivityTime;
        
        // If last activity was more than the threshold ago, mark as stalled
        if (timeSinceLastActivity > threshold) {
          state.agentLoop.isStalled = true;
          state.agentLoop.stalledSince = now;
        }
      }
    },
    resetStalledState: (state) => {
      state.agentLoop.isStalled = false;
      state.agentLoop.stalledSince = null;
    }
  }
});

// Thunk action creators
export const setLoadingAsync = (loadingState: LoadingState): AppThunk => (dispatch) => {
  dispatch(setLoading(loadingState));
};

export const setErrorAsync = (error: string | null): AppThunk => (dispatch) => {
  dispatch(setError(error));
};

export const setPreviewUrlAsync = (url: string | null): AppThunk => (dispatch) => {
  dispatch(setPreviewUrl(url));
};

// Thunk to ensure a reportId exists
export const ensureReportId = (): AppThunk => (dispatch, getState) => {
  const { reportId } = getState().report;
  
  // If there's no reportId yet, generate a new one
  if (!reportId) {
    const newReportId = generateUUID();
    dispatch(setReportId(newReportId));
  }
};

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
  setAgentLoop,
  addTransaction,
  updateTransaction,
  resetReport,
  setSessionTimeout,
  updateLastActivityTime,
  checkSessionTimeout,
  beginTransaction,
  completeTransaction,
  cleanupStaleTransactions,
  detectStalledAgentLoop,
  resetStalledState
} = reportSlice.actions;

// Export reducer
export default reportSlice.reducer;

// Placeholder exports for functions that might be imported elsewhere
// These can be implemented later with actual functionality
export const initAgentLoop = () => {
  console.warn('initAgentLoop was called but not implemented');
  return { type: 'NOT_IMPLEMENTED' };
};

export const updateAgentLoopProgress = () => {
  console.warn('updateAgentLoopProgress was called but not implemented');
  return { type: 'NOT_IMPLEMENTED' };
};

export const completeAgentLoop = () => {
  console.warn('completeAgentLoop was called but not implemented');
  return { type: 'NOT_IMPLEMENTED' };
};

export const failAgentLoop = () => {
  console.warn('failAgentLoop was called but not implemented');
  return { type: 'NOT_IMPLEMENTED' };
};

export const resetState = () => {
  console.warn('resetState was called but not implemented');
  return { type: 'NOT_IMPLEMENTED' };
}; 