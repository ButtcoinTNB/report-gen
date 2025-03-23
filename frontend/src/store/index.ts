import { configureStore, Action, ThunkAction } from '@reduxjs/toolkit';
import reportReducer from './reportSlice';
import cleanupMiddleware from './middleware/cleanupMiddleware';
import agentStatusMiddleware from './middleware/agentStatusMiddleware';
import { isServer, isDevelopment } from '../utils/environment';

// Configure the Redux store
export const store = configureStore({
  reducer: {
    report: reportReducer,
  },
  middleware: (getDefaultMiddleware) => {
    // Add browser-specific middleware only in browser environment
    const middleware = getDefaultMiddleware().concat(cleanupMiddleware);
    
    // Only include browser-specific middleware when not in SSR
    if (!isServer) {
      return middleware.concat(agentStatusMiddleware);
    }
    return middleware;
  },
  // Enable Redux DevTools in development
  devTools: isDevelopment,
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  Action<string>
>;

// Export the store
export default store; 