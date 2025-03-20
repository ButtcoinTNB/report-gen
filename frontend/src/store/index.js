import { configureStore } from '@reduxjs/toolkit';
import reportReducer from './reportSlice';

// Configure the Redux store
export const store = configureStore({
  reducer: {
    report: reportReducer,
  },
});

// Export the store
export default store; 