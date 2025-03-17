import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { 
  Container, 
  Typography, 
  Box, 
  Button, 
  CircularProgress, 
  Paper, 
  Card,
  CardContent,
  CardActions,
  Divider,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Grid
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import DescriptionIcon from '@mui/icons-material/Description';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { downloadReport, getReport } from '../api/report';

// Types
interface Report {
  id: number;
  template_id: number;
  title: string;
  content: string;
  formatted_file_path: string | null;
  created_at: string;
  updated_at: string | null;
  is_finalized: boolean;
  download_url?: string;
}

// Interface for download response
interface DownloadResponse {
  data: {
    download_url: string;
    [key: string]: any;
  };
  status: number;
}

const DownloadPage = () => {
  const router = useRouter();
  const { id } = router.query; // Get report ID from URL
  
  // State
  const [report, setReport] = useState<Report | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState('');
  
  // Fetch report data on component mount
  useEffect(() => {
    const fetchReport = async () => {
      if (!id) return;
      
      setIsLoading(true);
      try {
        // Call the API client function to fetch the report
        const reportData = await getReport(Number(id)) as Report;
        
        // Then get the download information
        const downloadData = await downloadReport(Number(id)) as DownloadResponse;
        
        setReport({
          ...reportData,
          download_url: downloadData.data.download_url
        });
      } catch (err) {
        console.error('Error fetching report:', err);
        setError('Failed to load report. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchReport();
  }, [id]);
  
  // Download the report PDF
  const handleDownload = async () => {
    if (!report || !report.download_url) return;
    
    setIsDownloading(true);
    try {
      // Open the download URL in a new tab
      window.open(report.download_url, '_blank');
    } catch (err) {
      console.error('Error downloading report:', err);
      setError('Failed to download report. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  };
  
  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  // If loading
  if (isLoading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 5, mb: 5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }
  
  // If no report or error
  if (!report && !isLoading) {
    return (
      <Container maxWidth="md" sx={{ mt: 5, mb: 5 }}>
        <Alert severity="error" sx={{ mb: 3 }}>
          {error || 'Report not found or not finalized yet.'}
        </Alert>
        <Button 
          variant="contained" 
          startIcon={<ArrowBackIcon />}
          onClick={() => router.push('/')}
        >
          Back to Home
        </Button>
      </Container>
    );
  }
  
  return (
    <Container maxWidth="md" sx={{ mt: 5, mb: 5 }}>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          Download Report
        </Typography>
        <Button 
          variant="outlined" 
          startIcon={<ArrowBackIcon />}
          onClick={() => router.push('/')}
        >
          Back to Home
        </Button>
      </Box>
      
      {/* Report Card */}
      <Card elevation={3} sx={{ mb: 4 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <DescriptionIcon sx={{ mr: 2, color: 'primary.main', fontSize: 40 }} />
            <Typography variant="h5" component="h2">
              {report?.title}
            </Typography>
          </Box>
          
          <Divider sx={{ mb: 3 }} />
          
          <List>
            <ListItem>
              <ListItemIcon>
                <CheckCircleIcon color="success" />
              </ListItemIcon>
              <ListItemText 
                primary="Status" 
                secondary={report?.is_finalized ? "Finalized" : "Draft"} 
              />
            </ListItem>
            
            <ListItem>
              <ListItemIcon>
                <AccessTimeIcon />
              </ListItemIcon>
              <ListItemText 
                primary="Created" 
                secondary={formatDate(report?.created_at || '')} 
              />
            </ListItem>
            
            {report?.updated_at && (
              <ListItem>
                <ListItemIcon>
                  <AccessTimeIcon />
                </ListItemIcon>
                <ListItemText 
                  primary="Last Updated" 
                  secondary={formatDate(report.updated_at)} 
                />
              </ListItem>
            )}
          </List>
        </CardContent>
        
        <CardActions sx={{ p: 2 }}>
          <Button 
            variant="contained" 
            color="primary" 
            fullWidth
            size="large"
            startIcon={<DownloadIcon />}
            onClick={handleDownload}
            disabled={isDownloading}
          >
            {isDownloading ? <CircularProgress size={24} /> : 'Download PDF Report'}
          </Button>
        </CardActions>
      </Card>
      
      {/* Preview section */}
      <Paper elevation={2} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Report Preview
        </Typography>
        
        <Divider sx={{ mb: 2 }} />
        
        <Box sx={{ 
          whiteSpace: 'pre-wrap', 
          fontFamily: 'monospace',
          bgcolor: 'grey.100',
          p: 2,
          borderRadius: 1,
          maxHeight: '300px',
          overflow: 'auto'
        }}>
          {report?.content}
        </Box>
        
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
          <Button 
            variant="outlined" 
            startIcon={<DownloadIcon />}
            onClick={handleDownload}
            disabled={isDownloading}
          >
            {isDownloading ? <CircularProgress size={24} /> : 'Download PDF Report'}
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default DownloadPage; 