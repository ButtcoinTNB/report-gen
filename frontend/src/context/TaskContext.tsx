import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { backOff } from 'exponential-backoff';

// Types for task state
export interface TaskStatus {
  taskId: string;
  status: 'idle' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  stage: string;
  message: string;
  estimatedTimeRemaining?: number;
  quality?: number;
  iterations?: number;
  error?: string;
}

interface TaskContextType {
  activeTask: TaskStatus | null;
  startTask: (taskId: string, taskType: string) => void;
  updateTaskProgress: (progress: number, stage: string, message: string) => void;
  updateTaskMetrics: (metrics: Partial<TaskStatus>) => void;
  completeTask: (result?: any) => void;
  failTask: (error: string) => void;
  cancelTask: () => void;
  resetTask: () => void;
  isProcessing: boolean;
}

// Create context with default values
const TaskContext = createContext<TaskContextType>({
  activeTask: null,
  startTask: () => {},
  updateTaskProgress: () => {},
  updateTaskMetrics: () => {},
  completeTask: () => {},
  failTask: () => {},
  cancelTask: () => {},
  resetTask: () => {},
  isProcessing: false
});

// Custom hook for using the task context
export const useTask = () => {
  const context = useContext(TaskContext);
  if (!context) {
    throw new Error('useTask must be used within a TaskProvider');
  }
  return context;
};

interface TaskProviderProps {
  children: ReactNode;
  pollingInterval?: number; // Milliseconds between status polls
  maxRetries?: number; // Maximum number of retries for polling
}

// Task provider component
export const TaskProvider: React.FC<TaskProviderProps> = ({ 
  children,
  pollingInterval = 2000, // Default to checking every 2 seconds
  maxRetries = 5 // Default max retries for polling
}) => {
  // Task state
  const [activeTask, setActiveTask] = useState<TaskStatus | null>(null);
  const [isPolling, setIsPolling] = useState<boolean>(false);
  const [failedAttempts, setFailedAttempts] = useState<number>(0);
  
  // Error handling
  const { handleError, wrapPromise } = useErrorHandler({
    showNotification: false // We'll handle task-specific notifications separately
  });
  
  // Check if task is processing
  const isProcessing = activeTask !== null && activeTask.status === 'in_progress';
  
  // Start a new task
  const startTask = useCallback((taskId: string, taskType: string) => {
    setActiveTask({
      taskId,
      status: 'in_progress',
      progress: 0,
      stage: 'initializing',
      message: 'Inizializzando...',
      estimatedTimeRemaining: undefined,
      quality: undefined,
      iterations: undefined
    });
    setIsPolling(true);
    setFailedAttempts(0);
  }, []);
  
  // Update task progress
  const updateTaskProgress = useCallback((progress: number, stage: string, message: string) => {
    setActiveTask(prev => {
      if (!prev) return null;
      return {
        ...prev,
        progress: Math.min(Math.max(0, progress), 100), // Ensure between 0-100
        stage,
        message
      };
    });
  }, []);
  
  // Update task metrics (quality, iterations, etc.)
  const updateTaskMetrics = useCallback((metrics: Partial<TaskStatus>) => {
    setActiveTask(prev => {
      if (!prev) return null;
      return {
        ...prev,
        ...metrics
      };
    });
  }, []);
  
  // Mark task as complete
  const completeTask = useCallback((result?: any) => {
    setActiveTask(prev => {
      if (!prev) return null;
      return {
        ...prev,
        status: 'completed',
        progress: 100,
        stage: 'completed',
        message: 'Elaborazione completata',
        estimatedTimeRemaining: 0
      };
    });
    setIsPolling(false);
  }, []);
  
  // Mark task as failed
  const failTask = useCallback((error: string) => {
    setActiveTask(prev => {
      if (!prev) return null;
      return {
        ...prev,
        status: 'failed',
        stage: 'failed',
        message: 'Elaborazione fallita',
        error
      };
    });
    setIsPolling(false);
  }, []);
  
  // Cancel the current task
  const cancelTask = useCallback(() => {
    if (!activeTask || !isProcessing) return;
    
    // Call API to cancel task
    wrapPromise(
      fetch(`/api/tasks/${activeTask.taskId}`, {
        method: 'DELETE'
      })
    )
    .then(() => {
      setActiveTask(prev => {
        if (!prev) return null;
        return {
          ...prev,
          status: 'cancelled',
          stage: 'cancelled',
          message: 'Elaborazione annullata'
        };
      });
    })
    .catch(error => {
      handleError(error, {
        showNotification: true,
        onError: () => {
          // If we can't cancel on the server, at least update the local state
          setActiveTask(prev => {
            if (!prev) return null;
            return {
              ...prev,
              status: 'cancelled',
              stage: 'cancelled',
              message: 'Elaborazione annullata (parziale)'
            };
          });
        }
      });
    })
    .finally(() => {
      setIsPolling(false);
    });
  }, [activeTask, isProcessing, wrapPromise, handleError]);
  
  // Reset task state
  const resetTask = useCallback(() => {
    setActiveTask(null);
    setIsPolling(false);
    setFailedAttempts(0);
  }, []);
  
  // Poll for task status updates with exponential backoff for failures
  useEffect(() => {
    if (!isPolling || !activeTask) return;
    
    // Track if component is mounted
    let isMounted = true;
    
    // Single polling attempt with exponential backoff on failure
    const fetchTaskStatus = async () => {
      try {
        // Use backoff for handling transient failures
        const result = await backOff(
          async () => {
            const response = await fetch(`/api/tasks/${activeTask.taskId}`);
            if (!response.ok) {
              const error = new Error(`Failed to fetch task status: ${response.statusText}`);
              // Track as a failure and possibly throw based on status
              setFailedAttempts(prev => prev + 1);
              throw error;
            }
            // Reset failures on success
            setFailedAttempts(0);
            return response.json();
          },
          {
            // Configure backoff
            numOfAttempts: 3, // Per individual polling cycle
            startingDelay: 1000,
            maxDelay: 5000,
            jitter: 'full', // Use 'full' jitter strategy
            retry: (error) => {
              // Don't retry 404s or if we've exceeded max failures
              if (error.message.includes('404') || failedAttempts >= maxRetries) {
                return false;
              }
              return true;
            }
          }
        );
        
        if (!isMounted) return;
        
        // Update local state with server data
        setActiveTask(prev => {
          if (!prev) return null;
          
          // If task is complete, failed, or cancelled, stop polling
          if (result.status === 'completed' || result.status === 'failed' || result.status === 'cancelled') {
            setIsPolling(false);
          }
          
          return {
            ...prev,
            status: result.status,
            progress: result.progress !== undefined ? result.progress : prev.progress,
            stage: result.current_stage || prev.stage,
            message: result.message || prev.message,
            estimatedTimeRemaining: result.time_remaining,
            quality: result.quality_score,
            iterations: result.iterations,
            error: result.error
          };
        });
        
      } catch (error) {
        if (!isMounted) return;
        
        handleError(error, { 
          showNotification: failedAttempts >= 3, // Only show notifications after multiple failures
          logError: true 
        });
        
        // If we've exceeded max retries, stop polling
        if (failedAttempts >= maxRetries) {
          setIsPolling(false);
          
          // Update task state to failed
          setActiveTask(prev => {
            if (!prev) return null;
            return {
              ...prev,
              status: 'failed',
              stage: 'failed',
              message: 'Impossibile ottenere aggiornamenti dal server',
              error: 'Connection to server lost'
            };
          });
        }
      }
    };
    
    // Set up polling interval with jitter to avoid thundering herd
    const jitter = Math.random() * 500; // Add up to 500ms of jitter
    const interval = setInterval(fetchTaskStatus, pollingInterval + jitter);
    
    // Initial poll
    fetchTaskStatus();
    
    // Cleanup interval on unmount
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isPolling, activeTask, pollingInterval, failedAttempts, maxRetries, handleError]);
  
  // Context value
  const value = {
    activeTask,
    startTask,
    updateTaskProgress,
    updateTaskMetrics,
    completeTask,
    failTask,
    cancelTask,
    resetTask,
    isProcessing
  };
  
  return (
    <TaskContext.Provider value={value}>
      {children}
    </TaskContext.Provider>
  );
};

export default TaskProvider; 