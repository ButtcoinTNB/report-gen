import React from 'react';
import { Alert, Button, Paper, Typography, Box } from '@mui/material';
import { ErrorOutline } from '@mui/icons-material';

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to monitoring service
    console.error('Error caught by boundary:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Paper 
          elevation={3}
          sx={{
            p: 4,
            m: 2,
            maxWidth: 600,
            mx: 'auto',
            textAlign: 'center'
          }}
        >
          <ErrorOutline 
            color="error" 
            sx={{ fontSize: 64, mb: 2 }}
          />
          
          <Typography variant="h5" gutterBottom>
            Qualcosa è andato storto
          </Typography>
          
          <Typography variant="body1" color="text.secondary" paragraph>
            Si è verificato un errore imprevisto. Prova a ricaricare la pagina o contatta il supporto se il problema persiste.
          </Typography>
          
          <Alert severity="error" sx={{ mb: 2, mx: 'auto', maxWidth: 400 }}>
            {this.state.error?.message || 'Errore sconosciuto'}
          </Alert>
          
          {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
            <Box 
              component="pre"
              sx={{
                mt: 2,
                p: 2,
                bgcolor: 'grey.100',
                borderRadius: 1,
                overflow: 'auto',
                fontSize: '0.875rem',
                textAlign: 'left'
              }}
            >
              {this.state.errorInfo.componentStack}
            </Box>
          )}
          
          <Box sx={{ mt: 3 }}>
            <Button
              variant="contained"
              onClick={() => window.location.reload()}
              sx={{ mr: 2 }}
            >
              Ricarica Pagina
            </Button>
            
            <Button
              variant="outlined"
              onClick={this.handleReset}
            >
              Riprova
            </Button>
          </Box>
        </Paper>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary; 