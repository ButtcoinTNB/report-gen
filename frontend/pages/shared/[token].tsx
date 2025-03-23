import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import { GetServerSideProps } from 'next';
import { 
  Container, 
  Typography, 
  CircularProgress, 
  Paper, 
  Alert, 
  Box,
  Link as MuiLink
} from '@mui/material';
import Link from 'next/link';
import { shareService } from '../../src/utils/supabase';
import { useAppDispatch } from '../../src/store/hooks';
import { setReportId } from '../../src/store/reportSlice';
import EnhancedReportDownloader from '../../src/components/EnhancedReportDownloader';

interface SharedReportPageProps {
  reportId: string | null;
  error?: string;
}

export const getServerSideProps: GetServerSideProps<SharedReportPageProps> = async (context) => {
  const { token } = context.params || {};
  
  if (!token || typeof token !== 'string') {
    return {
      props: {
        reportId: null,
        error: 'Invalid share link'
      }
    };
  }
  
  try {
    // Get the report ID associated with this token
    const reportId = await shareService.getReportIdFromToken(token);
    
    if (!reportId) {
      return {
        props: {
          reportId: null,
          error: 'This share link has expired or is invalid'
        }
      };
    }
    
    return {
      props: {
        reportId
      }
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return {
      props: {
        reportId: null,
        error: `Could not load shared report: ${errorMessage}`
      }
    };
  }
};

const SharedReportPage: React.FC<SharedReportPageProps> = ({ reportId, error }) => {
  const router = useRouter();
  const dispatch = useAppDispatch();
  
  useEffect(() => {
    // Set the report ID in Redux when the component mounts
    if (reportId) {
      dispatch(setReportId(reportId));
    }
  }, [reportId, dispatch]);
  
  if (error) {
    return (
      <Container maxWidth="md" sx={{ my: 5 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
          <Typography variant="body1" sx={{ mb: 2 }}>
            This shared report link is invalid or has expired. Please contact the person who shared this link with you.
          </Typography>
          <Link href="/" passHref>
            <MuiLink>Return to home page</MuiLink>
          </Link>
        </Paper>
      </Container>
    );
  }
  
  if (!reportId) {
    return (
      <Container maxWidth="lg" sx={{ mt: 5, mb: 5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }
  
  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4, mb: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Shared Report
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          This is a shared report. You can view, download, or print this report.
        </Typography>
      </Box>
      
      <EnhancedReportDownloader />
    </Container>
  );
};

export default SharedReportPage; 