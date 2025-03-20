import { configureStore, Action, ThunkAction } from '@reduxjs/toolkit';
import reportReducer from './reportSlice';

// Configure the Redux store
export const store = configureStore({
  reducer: {
    report: reportReducer,
  },
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