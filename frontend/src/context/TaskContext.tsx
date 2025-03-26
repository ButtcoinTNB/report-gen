import React, { createContext, useContext, useState, useCallback, useEffect, useMemo } from 'react';
import { v4 as uuid } from 'uuid';
import { useSnackbar } from 'notistack';
import reportService from '../services/ReportService';

// Define the stages of the process following the complete flow
export type ProcessStage = 
  | 'idle'
  | 'upload'
  | 'extraction'
  | 'analysis'
  | 'writer'
  | 'reviewer'
  | 'refinement'
  | 'formatting'
  | 'finalization';

// Define the possible task statuses
export type TaskStatus = 
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'cancelled';

// Define uploaded file information
export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  uploadedAt: Date;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  progress: number;
  url?: string;
}

// Define document version interface
export interface DocumentVersion {
  id: string;
  createdAt: Date;
  label: string;
  description?: string;
  isCurrent: boolean;
  stage: ProcessStage;
  url?: string;
}

// Define the task state interface
export interface TaskState {
  id: string;
  status: TaskStatus;
  stage: ProcessStage;
  progress: number;
  message: string;
  error?: string;
  startTime?: Date;
  estimatedTimeRemaining?: number;
  currentReportId?: string;
  currentVersionId?: string;
  versions?: DocumentVersion[];
  uploadedFiles?: UploadedFile[];
  metrics?: {
    uploadedFiles: number;
    totalFiles: number;
  };
}

// Valid transitions between task stages
const validTransitions: Record<ProcessStage, ProcessStage[]> = {
  idle: ['upload'],
  upload: ['extraction'],
  extraction: ['analysis', 'idle'],  // Can go back to idle if extraction fails
  analysis: ['writer', 'extraction'], // Can retry extraction if needed
  writer: ['reviewer', 'analysis'],  // Can go back to analysis if needed
  reviewer: ['refinement', 'writer'], // Can go back to writer stage if needed
  refinement: ['formatting', 'reviewer'], // Can restart review process
  formatting: ['finalization', 'refinement'], // Can go back to refinement
  finalization: ['idle'] // Start a new task
};

export type TaskContextType = {
  task: TaskState;
  updateTask: (updates: Partial<TaskState>) => void;
  transitionToStage: (newStage: ProcessStage) => boolean;
  resetTask: () => void;
  createVersion: (reportId: string, label: string, description?: string) => Promise<string | null>;
  switchVersion: (versionId: string) => Promise<boolean>;
  compareVersions: (versionIds: [string, string]) => Promise<any>;
  downloadVersion: (versionId: string) => Promise<boolean>;
  updateMetrics: (metrics: { uploadedFiles: number; totalFiles: number; }) => void;
  updateProgress: (progress: number, message?: string) => void;
};

// Default context value
const defaultTaskContext: TaskContextType = {
  task: {
    id: '',
    status: 'pending',
    stage: 'idle',
    progress: 0,
    message: 'Ready to start',
    versions: [],
    metrics: {
      uploadedFiles: 0,
      totalFiles: 0
    }
  },
  updateTask: () => {},
  transitionToStage: () => false,
  resetTask: () => {},
  createVersion: async () => null,
  switchVersion: async () => false,
  compareVersions: async () => null,
  downloadVersion: async () => false,
  updateMetrics: () => {},
  updateProgress: () => {}
};

// Create the context
export const TaskContext = createContext<TaskContextType>(defaultTaskContext);

// Hook to use the task context
export const useTask = () => useContext(TaskContext);

// Provider component
export const TaskProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [task, setTask] = useState<TaskState>(defaultTaskContext.task);
  const { enqueueSnackbar } = useSnackbar();

  // Update task state partially
  const updateTask = useCallback((updates: Partial<TaskState>) => {
    setTask(prevTask => ({ ...prevTask, ...updates }));
  }, []);

  // Update progress with optional message
  const updateProgress = useCallback((progress: number, message?: string) => {
    updateTask({ 
      progress: Math.min(100, Math.max(0, progress)),
      message: message || task.message
    });
  }, [updateTask, task.message]);

  // Update metrics
  const updateMetrics = useCallback((metrics: { uploadedFiles: number; totalFiles: number; }) => {
    updateTask({ metrics });
  }, [updateTask]);

  // Transition to a new stage with validation
  const transitionToStage = useCallback((newStage: ProcessStage): boolean => {
    const currentStage = task.stage;
    
    // Check if the transition is valid
    if (!validTransitions[currentStage].includes(newStage)) {
      console.error(`Invalid transition from ${currentStage} to ${newStage}`);
      return false;
    }
    
    // Update the task with the new stage
    updateTask({ 
      stage: newStage,
      message: `Transitioned to ${newStage} stage`
    });
    
    return true;
  }, [task.stage, updateTask]);

  // Reset task to initial state
  const resetTask = useCallback(() => {
    setTask({
      ...defaultTaskContext.task,
      id: uuid() // Generate a new task ID
    });
  }, []);

  // Create a new document version
  const createVersion = useCallback(async (
    reportId: string, 
    label: string, 
    description?: string
  ): Promise<string | null> => {
    try {
      if (!reportId) {
        throw new Error('Report ID is required to create a version');
      }
      
      // Call the report service to create version
      const result = await reportService.createVersion(reportId, {
        label,
        description,
        stage: task.stage
      });
      
      // Create a new version object from the result
      const newVersion: DocumentVersion = {
        id: result.id,
        createdAt: new Date(result.createdAt),
        label,
        description,
        isCurrent: true,
        stage: task.stage,
        url: result.url
      };
      
      // Update current versions (mark previous current as not current)
      const updatedVersions = task.versions ? 
        task.versions.map(v => ({
          ...v,
          isCurrent: false
        })).concat(newVersion) : 
        [newVersion];
      
      updateTask({
        versions: updatedVersions,
        currentVersionId: newVersion.id
      });
      
      enqueueSnackbar(`Version ${label} created successfully`, { 
        variant: 'success',
        autoHideDuration: 3000
      });
      
      return newVersion.id;
    } catch (error) {
      console.error('Failed to create version:', error);
      if (error instanceof Error) {
        enqueueSnackbar(`Failed to create version: ${error.message}`, { 
          variant: 'error',
          autoHideDuration: 5000
        });
      }
      return null;
    }
  }, [task.stage, task.versions, updateTask, enqueueSnackbar]);

  // Switch to a different version
  const switchVersion = useCallback(async (versionId: string): Promise<boolean> => {
    try {
      if (!task.versions || task.versions.length === 0) {
        return false;
      }
      
      const version = task.versions.find(v => v.id === versionId);
      if (!version) {
        return false;
      }
      
      // Load version content if needed
      await reportService.getVersion(versionId);
      
      // Update current version without changing version array
      updateTask({
        currentVersionId: versionId,
        versions: task.versions.map(v => ({
          ...v,
          isCurrent: v.id === versionId
        }))
      });
      
      enqueueSnackbar(`Switched to version ${version.label}`, { 
        variant: 'info',
        autoHideDuration: 3000
      });
      
      return true;
    } catch (error) {
      console.error('Failed to switch version:', error);
      if (error instanceof Error) {
        enqueueSnackbar(`Failed to switch version: ${error.message}`, { 
          variant: 'error',
          autoHideDuration: 5000
        });
      }
      return false;
    }
  }, [task.versions, updateTask, enqueueSnackbar]);

  // Compare two versions
  const compareVersions = useCallback(async (versionIds: [string, string]) => {
    try {
      const [versionId1, versionId2] = versionIds;
      
      // Get the comparison result from the report service
      const result = await reportService.compareVersions(versionId1, versionId2);
      return result;
    } catch (error) {
      console.error('Failed to compare versions:', error);
      if (error instanceof Error) {
        enqueueSnackbar(`Failed to compare versions: ${error.message}`, { 
          variant: 'error',
          autoHideDuration: 5000
        });
      }
      return null;
    }
  }, [enqueueSnackbar]);

  // Download a specific version
  const downloadVersion = useCallback(async (versionId: string): Promise<boolean> => {
    try {
      const version = task.versions?.find(v => v.id === versionId);
      if (!version) {
        return false;
      }
      
      // Use the report service to download the version
      await reportService.downloadVersion(versionId, `report-${versionId}.docx`);
      
      return true;
    } catch (error) {
      console.error('Failed to download version:', error);
      if (error instanceof Error) {
        enqueueSnackbar(`Failed to download version: ${error.message}`, { 
          variant: 'error',
          autoHideDuration: 5000
        });
      }
      return false;
    }
  }, [task.versions, enqueueSnackbar]);

  // Initialize task on mount
  useEffect(() => {
    if (!task.id) {
      resetTask();
    }
  }, [resetTask, task.id]);

  const contextValue = useMemo(() => ({
    task,
    updateTask,
    transitionToStage,
    resetTask,
    createVersion,
    switchVersion,
    compareVersions,
    downloadVersion,
    updateMetrics,
    updateProgress
  }), [
    task, 
    updateTask, 
    transitionToStage, 
    resetTask, 
    createVersion, 
    switchVersion, 
    compareVersions, 
    downloadVersion,
    updateMetrics,
    updateProgress
  ]);

  return (
    <TaskContext.Provider value={contextValue}>
      {children}
    </TaskContext.Provider>
  );
}; 