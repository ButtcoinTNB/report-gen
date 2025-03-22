import { store } from '../store';
import { checkSessionTimeout, updateLastActivityTime, setBackgroundUpload } from '../store/reportSlice';
import { debounce } from 'lodash';
import { logger } from './logger';

/**
 * Class for managing user session and timeouts
 * This class handles the cleanup of resources and manages user inactivity
 */
export class SessionManager {
  private static instance: SessionManager;
  private timeoutInterval: number = 60000; // Check every minute
  private intervalId: number | null = null;
  private readonly activityEvents = [
    'mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'
  ];
  
  private constructor() {
    this.setupActivityListeners();
    this.startSessionChecks();
    
    // Handle page unload to clean up resources
    window.addEventListener('beforeunload', this.handlePageUnload);
  }
  
  /**
   * Get the singleton instance
   */
  public static getInstance(): SessionManager {
    if (!SessionManager.instance) {
      SessionManager.instance = new SessionManager();
    }
    return SessionManager.instance;
  }
  
  /**
   * Initialize the session manager
   */
  public init(): void {
    logger.info('Session manager initialized');
  }
  
  /**
   * Set up event listeners for user activity
   */
  private setupActivityListeners(): void {
    // Use debounce to prevent excessive state updates
    const debouncedActivityHandler = debounce(this.handleUserActivity.bind(this), 300);
    
    // Add event listeners for user activity
    this.activityEvents.forEach(eventType => {
      document.addEventListener(eventType, debouncedActivityHandler, { passive: true });
    });
  }
  
  /**
   * Handle user activity events
   */
  private handleUserActivity(): void {
    store.dispatch(updateLastActivityTime());
  }
  
  /**
   * Start regular checks for session timeout
   */
  private startSessionChecks(): void {
    if (this.intervalId === null) {
      this.intervalId = window.setInterval(() => {
        store.dispatch(checkSessionTimeout());
      }, this.timeoutInterval);
    }
  }
  
  /**
   * Handle page unload to clean up resources
   */
  private handlePageUnload = (): void => {
    // Get the current state
    const state = store.getState();
    const { reportId, backgroundUpload } = state.report;
    
    // If there's an active report and uploads, trigger cleanup
    if (reportId && backgroundUpload.isUploading) {
      // Use the sync version of navigator.sendBeacon for reliable delivery
      // during page unload
      try {
        const cleanupData = JSON.stringify({ 
          reportId 
        });
        
        navigator.sendBeacon(
          '/api/cleanup/temp-files',
          new Blob([cleanupData], { type: 'application/json' })
        );
        
        logger.info(`Sent cleanup request for report: ${reportId}`);
      } catch (error) {
        logger.error('Failed to send cleanup request before page unload', error);
      }
    }
  }
  
  /**
   * Stop session checks
   */
  public stopSessionChecks(): void {
    if (this.intervalId !== null) {
      window.clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
  
  /**
   * Clean up resources when component is unloaded
   */
  public cleanup(): void {
    // Remove event listeners
    const debouncedActivityHandler = debounce(this.handleUserActivity.bind(this), 300);
    this.activityEvents.forEach(eventType => {
      document.removeEventListener(eventType, debouncedActivityHandler);
    });
    
    // Remove beforeunload handler
    window.removeEventListener('beforeunload', this.handlePageUnload);
    
    // Stop interval
    this.stopSessionChecks();
  }
}

export default SessionManager; 