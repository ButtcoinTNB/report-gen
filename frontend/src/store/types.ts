export type LoadingStage = 
  | 'initial'
  | 'uploading'
  | 'analyzing'
  | 'generating'
  | 'refining'
  | 'downloading'
  | 'formatting'
  | 'saving'
  | 'preview'
  | 'download'
  | 'share'
  | 'metadata'
  | 'error'
  | 'complete';

export type AgentStage =
  | 'idle'
  | 'initializing'
  | 'writing'
  | 'reviewing'
  | 'running'
  | 'error'
  | 'complete';

export interface LoadingState {
  isLoading: boolean;
  stage?: LoadingStage;
  message?: string;
  progress?: number;
}

export interface StateTransaction {
  id: string;
  type: string;
  operation: 'cancel' | 'reconnect' | 'update' | 'complete';
  status: 'pending' | 'completed' | 'failed';
  error?: string;
  retryCount?: number;
  isPending?: boolean;
  startTime?: number;
  taskId?: string;
}

export interface BackgroundUploadState {
  isUploading: boolean;
  progress: number;
  error: string | null;
  totalFiles?: number;
  uploadedFiles?: number;
  uploadStartTime?: number;
  uploadSessionId?: string;
  shouldCleanup?: boolean;
  cleanupReportId?: string;
}

export interface AgentLoopState {
  isRunning: boolean;
  isStalled: boolean;
  taskId: string | null;
  isInitializing: boolean;
  progress: number;
  stage: AgentStage;
  currentIteration: number;
  totalIterations: number;
  message: string;
  error: string | null;
  canCancel: boolean;
  estimatedTimeRemaining: number | null;
  startTime: number | null;
  transactionId: string | null;
  stalledSince: number | null;
}

export interface ReportState {
  activeStep: number;
  reportId: string | null;
  content: string | null;
  previewUrl: string | null;
  loading: LoadingState;
  documentIds: string[];
  additionalInfo: string;
  error: string | null;
  backgroundUpload: BackgroundUploadState;
  agentLoop: AgentLoopState;
  sessionTimeout: number;
  lastActivityTime: number;
  pendingTransactions: StateTransaction[];
}

export interface ReportVersion {
  id: string;
  report_id: string;
  version_number: number;
  content: string;
  created_at: string;
  created_by: string;
  changes_description?: string;
}

export interface ReportVersionResponse {
  versions: ReportVersion[];
  current_version: number;
} 