import React from 'react';
import type { AppProps } from 'next/app';
import { SnackbarProvider } from 'notistack';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { ErrorBoundary } from 'react-error-boundary';
import * as Sentry from "@sentry/react";

// Initialize Sentry as early as possible
Sentry.init({
  dsn: "https://314f46a05921664f4fd83adb38350878@o4509033743646720.ingest.de.sentry.io/4509033772875856",
  // This sets the sample rate to be 10%. You may want this to be 100% while
  // in development and sample at a lower rate in production
  replaysSessionSampleRate: 0.1,
  // If the entire session is not sampled, use the below sample rate to sample
  // sessions when an error occurs.
  replaysOnErrorSampleRate: 1.0,
});

import { TaskProvider } from '../context/TaskContext';
import TaskDashboard from '../components/TaskDashboard';
import '../styles/globals.css';

// Create a theme instance
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

// Error fallback component
const ErrorFallback = ({ error }: { error: Error }) => {
  return (
    <div role="alert" style={{
      padding: '20px',
      margin: '20px',
      border: '1px solid #f44336',
      borderRadius: '4px',
      backgroundColor: '#ffebee'
    }}>
      <h2>Qualcosa è andato storto 😥</h2>
      <p>Si è verificato un errore imprevisto:</p>
      <pre style={{ padding: '10px', backgroundColor: '#f5f5f5', overflow: 'auto' }}>
        {error.message}
      </pre>
      <button onClick={() => window.location.reload()} style={{
        padding: '8px 16px',
        backgroundColor: '#f44336',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer'
      }}>
        Ricarica pagina
      </button>
    </div>
  );
};

function MyApp({ Component, pageProps }: AppProps) {
  // Use TaskDashboard as the main component for the entire app
  const useCustomApp = process.env.NEXT_PUBLIC_USE_DASHBOARD === 'true';
  
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <SnackbarProvider 
          maxSnack={3}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          autoHideDuration={5000}
        >
          <TaskProvider>
            {useCustomApp ? (
              <TaskDashboard />
            ) : (
              <Component {...pageProps} />
            )}
          </TaskProvider>
        </SnackbarProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default MyApp; 