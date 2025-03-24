import React from 'react';
import { Button, Typography, Box, Paper } from '@mui/material';

/**
 * SentryDebug component for testing Sentry error reporting
 * This component contains a button that deliberately throws an error when clicked
 */
const SentryDebug: React.FC = () => {
  const throwError = () => {
    throw new Error("This is an intentional error to test Sentry integration!");
  };

  return (
    <Paper 
      elevation={3} 
      sx={{ 
        p: 3, 
        m: 2, 
        backgroundColor: '#fffbf0', 
        border: '1px dashed #ff9800' 
      }}
    >
      <Box display="flex" flexDirection="column" alignItems="flex-start" gap={2}>
        <Typography variant="h6" color="warning.main">Sentry Debug Tools</Typography>
        <Typography variant="body2">
          This section is for testing Sentry error reporting. The button below will intentionally 
          throw an error which should be captured by Sentry if configured correctly.
        </Typography>
        <Button 
          variant="contained" 
          color="warning" 
          onClick={throwError}
          size="small"
        >
          Test Sentry Error Tracking
        </Button>
      </Box>
    </Paper>
  );
};

export default SentryDebug; 