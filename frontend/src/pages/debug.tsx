import React from 'react';
import { Container, Typography, Box, Divider, Paper } from '@mui/material';
import SentryDebug from '../components/SentryDebug';
import Head from 'next/head';

/**
 * Debug page with various debugging tools
 */
const DebugPage: React.FC = () => {
  return (
    <>
      <Head>
        <title>Debug Tools - Insurance Report Generator</title>
      </Head>
      <Container maxWidth="md">
        <Box sx={{ my: 4 }}>
          <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h4" component="h1" gutterBottom>
              Debug Tools
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              This page contains various tools for debugging and testing the application.
              Only use these in development or when instructed by technical support.
            </Typography>
          </Paper>

          <Divider sx={{ my: 3 }} />
          
          <Typography variant="h5" gutterBottom>
            Error Reporting
          </Typography>
          
          {/* Sentry Debug Component */}
          <SentryDebug />
          
          <Divider sx={{ my: 3 }} />
          
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 4 }}>
            These tools are for development and debugging purposes only.
          </Typography>
        </Box>
      </Container>
    </>
  );
};

export default DebugPage; 