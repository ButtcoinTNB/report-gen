import dynamic from 'next/dynamic';
import { ComponentType } from 'react';
import { Box, Skeleton, CircularProgress } from '@mui/material';

// Loading placeholders
const DocumentPreviewLoading = () => (
  <Box sx={{ p: 3, bgcolor: 'background.paper', minHeight: '500px' }}>
    <Skeleton variant="rectangular" width="100%" height={40} sx={{ mb: 2 }} />
    <Skeleton variant="rectangular" width="100%" height={400} />
  </Box>
);

const DownloadProgressLoading = () => (
  <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
    <CircularProgress />
  </Box>
);

const ReportSummaryLoading = () => (
  <Box sx={{ p: 3, bgcolor: 'background.paper', my: 3 }}>
    <Skeleton variant="rectangular" width="100%" height={200} />
  </Box>
);

// Dynamically import heavy components to reduce initial bundle size
export const DocumentPreview = dynamic(
  () => import('./DocumentPreview'),
  { 
    loading: () => <DocumentPreviewLoading />,
    ssr: false // Disable server-side rendering since this component uses browser APIs
  }
) as ComponentType<React.ComponentProps<typeof import('./DocumentPreview').default>>;

export const DownloadProgressTracker = dynamic(
  () => import('./DownloadProgressTracker'),
  { 
    loading: () => <DownloadProgressLoading />,
    ssr: false // Disable server-side rendering since this component uses browser APIs
  }
) as ComponentType<React.ComponentProps<typeof import('./DownloadProgressTracker').default>>;

export const ReportSummary = dynamic(
  () => import('./ReportSummary'),
  { 
    loading: () => <ReportSummaryLoading />
  }
) as ComponentType<React.ComponentProps<typeof import('./ReportSummary').default>>; 