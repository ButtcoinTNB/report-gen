import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Head from 'next/head';
import '../styles/globals.css';

// Create an Apple-inspired theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#0071e3', // Apple blue
      light: '#47a9ff',
      dark: '#0058b0',
    },
    secondary: {
      main: '#06c149', // Success green
      light: '#39d66d',
      dark: '#008c32',
    },
    error: {
      main: '#ff3b30', // Apple red
    },
    warning: {
      main: '#ff9500', // Apple orange
    },
    info: {
      main: '#5ac8fa', // Apple light blue
    },
    success: {
      main: '#34c759', // Apple green
    },
    background: {
      default: '#f5f5f7', // Light gray background (Apple website color)
      paper: '#ffffff',
    },
    text: {
      primary: '#1d1d1f', // Apple dark gray for text
      secondary: '#86868b', // Apple secondary text color
    },
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif',
    h1: {
      fontWeight: 600,
      fontSize: '2.5rem',
    },
    h2: {
      fontWeight: 600,
      fontSize: '2rem',
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.5rem',
    },
    h4: {
      fontWeight: 500,
      fontSize: '1.25rem',
    },
    button: {
      textTransform: 'none', // Apple doesn't use uppercase buttons
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 8, // Apple uses rounded corners but not too rounded
  },
  shadows: [
    'none',
    '0px 2px 4px rgba(0, 0, 0, 0.05)',
    '0px 4px 8px rgba(0, 0, 0, 0.05)',
    '0px 8px 16px rgba(0, 0, 0, 0.05)',
    '0px 12px 24px rgba(0, 0, 0, 0.05)',
    // ... rest of the shadows
    ...Array(20).fill('0px 12px 24px rgba(0, 0, 0, 0.05)'),
  ],
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '999px', // Pill shaped buttons
          padding: '8px 16px',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
        contained: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0px 2px 12px rgba(0, 0, 0, 0.05)',
        },
        rounded: {
          borderRadius: 12,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0px 2px 12px rgba(0, 0, 0, 0.05)',
          borderRadius: 12,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: 'none',
          borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(10px)',
          color: '#1d1d1f',
        },
      },
    },
  },
});

export default function App({ Component, pageProps }) {
  return (
    <>
      <Head>
        <title>Generatore di Perizie</title>
        <meta name="description" content="Genera perizie con AI" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Component {...pageProps} />
      </ThemeProvider>
    </>
  );
} 