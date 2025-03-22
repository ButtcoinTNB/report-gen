import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from './theme';
import HomePage from './pages/HomePage';
import ReportPage from './pages/ReportPage';
import NotFoundPage from './pages/NotFoundPage';
import SessionManager from './utils/SessionManager';

function App() {
  // Initialize the session manager
  useEffect(() => {
    const sessionManager = SessionManager.getInstance();
    sessionManager.init();
    
    // Clean up on component unmount
    return () => {
      sessionManager.cleanup();
    };
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/report/:reportId?" element={<ReportPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App; 