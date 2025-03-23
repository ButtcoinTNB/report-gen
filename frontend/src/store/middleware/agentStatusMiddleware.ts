import { Middleware } from 'redux';
import { detectStalledAgentLoop } from '../reportSlice';
import { logger } from '../../utils/logger';

// Type to represent the state shape
interface State {
  report: {
    agentLoop: {
      isInitializing: boolean;
      isRunning: boolean;
    }
  }
}

/**
 * Middleware for handling agent loop status monitoring
 * This middleware sets up periodic checks for stalled processes
 * and automatically dispatches actions to update the stalled status
 */
const agentStatusMiddleware: Middleware<{}, State> = store => {
  // Set up interval for periodic stalled status checks
  let checkInterval: number | null = null;
  
  // Initialize network status monitoring
  let isOnline = navigator.onLine;
  
  // Handle online status changes
  const handleOnlineStatus = () => {
    const wasOffline = !isOnline;
    isOnline = navigator.onLine;
    
    // Log status change
    if (wasOffline && isOnline) {
      logger.info('Network connection restored');
      
      // Force a stalled check when coming back online
      const state = store.getState();
      if (
        state.report.agentLoop.isInitializing || 
        state.report.agentLoop.isRunning
      ) {
        store.dispatch(detectStalledAgentLoop());
      }
    } else if (!isOnline) {
      logger.warn('Network connection lost');
    }
  };
  
  // Add event listeners for online/offline events
  window.addEventListener('online', handleOnlineStatus);
  window.addEventListener('offline', handleOnlineStatus);
  
  return next => action => {
    const result = next(action);
    const state = store.getState();
    
    // Start monitoring when agent loop becomes active
    if (
      (state.report.agentLoop.isInitializing || state.report.agentLoop.isRunning) && 
      !checkInterval
    ) {
      logger.info('Starting agent status monitoring');
      
      // Check every 15 seconds
      checkInterval = window.setInterval(() => {
        store.dispatch(detectStalledAgentLoop());
      }, 15000);
    }
    
    // Stop monitoring when agent loop becomes inactive
    if (
      !state.report.agentLoop.isInitializing && 
      !state.report.agentLoop.isRunning && 
      checkInterval
    ) {
      logger.info('Stopping agent status monitoring');
      clearInterval(checkInterval);
      checkInterval = null;
    }
    
    return result;
  };
};

export default agentStatusMiddleware; 