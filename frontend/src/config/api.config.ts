/**
 * API Configuration
 * Contains parameters for API communication, polling, timeouts, and retries
 */

export const apiConfig = {
  // Task polling configuration
  polling: {
    interval: 10000, // Poll every 10 seconds by default
    maxPolls: 60,    // Maximum number of polls (10 minutes at 10s intervals)
    initialDelay: 2000, // Initial delay before first poll
  },
  
  // Timeouts configuration (all in milliseconds)
  timeouts: {
    agentInit: 15000,        // Agent loop initialization (15 seconds)
    agentIteration: 300000,  // Agent iteration (5 minutes)
    fileUpload: 180000,      // File upload (3 minutes per file)
    cancelOperation: 10000,  // Cancellation operation (10 seconds)
  },
  
  // Retry configuration
  retry: {
    maxRetries: 3,           // Maximum number of automatic retries
    backoffFactor: 2,        // Exponential backoff factor
    initialBackoff: 1000,    // Initial backoff in milliseconds
  },
  
  // Progress scaling (for mapping different progress scales)
  progressScaling: {
    agentInit: {
      min: 0,
      max: 20
    },
    agentProcessing: {
      min: 20,
      max: 90
    },
    agentCompletion: {
      min: 90,
      max: 100
    }
  },
  
  // WebSocket configuration
  webSocket: {
    enabled: true,           // Enable WebSocket when available
    reconnectInterval: 2000, // Reconnect interval in milliseconds
    maxReconnectAttempts: 5, // Maximum reconnection attempts
    fallbackToPolling: true  // Fall back to polling if WebSocket fails
  },
  
  // Endpoints (to avoid hardcoding)
  endpoints: {
    fileUpload: '/api/upload/files',
    agentLoop: '/api/agent-loop/generate-report',
    taskStatus: '/api/agent-loop/task-status',
    cancelTask: '/api/agent-loop/cancel-task',
    taskEvents: '/api/agent-loop/task-events'
  }
};

export default apiConfig; 