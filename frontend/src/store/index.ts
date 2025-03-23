import { configureStore, Action, ThunkAction } from '@reduxjs/toolkit';
import reportReducer from './reportSlice';
import cleanupMiddleware from './middleware/cleanupMiddleware';
import agentStatusMiddleware from './middleware/agentStatusMiddleware';

// Configure the Redux store
export const store = configureStore({
  reducer: {
    report: reportReducer,
  },
  middleware: (getDefaultMiddleware) => 
    getDefaultMiddleware().concat(cleanupMiddleware, agentStatusMiddleware),
  // Enable Redux DevTools in development
  devTools: process.env.NODE_ENV !== 'production',
});

// Define RootState and AppDispatch types
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