import { Middleware } from 'redux';
import { RootState } from '../store';
import { setBackgroundUpload } from '../reportSlice';
import axios from 'axios';
import { logger } from '../../utils/logger';

/**
 * Middleware for handling cleanup of temporary files
 * This middleware listens for actions that might require file cleanup
 * such as session expiry, component unmounting, or user leaving the page
 */
export const cleanupMiddleware: Middleware<{}, RootState> = store => next => action => {
  // First, pass the action to the next middleware
  const result = next(action);
  
  // Handle cleanup after the action has been processed
  if (
    action.type === setBackgroundUpload.type && 
    action.payload?.shouldCleanup && 
    (action.payload?.cleanupReportId || store.getState().report.reportId)
  ) {
    const reportId = action.payload.cleanupReportId || store.getState().report.reportId;
    
    // Call the cleanup API
    if (reportId) {
      logger.info(`Cleaning up temporary files for report ${reportId}`);
      
      // Make the API call
      axios.post('/api/cleanup/temp-files', { reportId })
        .then(() => {
          logger.info(`Successfully cleaned up temporary files for report ${reportId}`);
        })
        .catch(error => {
          logger.error(`Failed to clean up temporary files for report ${reportId}:`, error);
        });
    }
  }
  
  return result;
};

export default cleanupMiddleware; 