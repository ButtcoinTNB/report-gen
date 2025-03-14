import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { 
  Container, 
  Box, 
  Typography, 
  Button, 
  TextField, 
  CircularProgress,
  Paper,
  Divider,
  Grid,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions
} from '@mui/material';
import dynamic from 'next/dynamic';
import 'easymde/dist/easymde.min.css';
import { getReport, updateReport, refineReport, finalizeReport } from '../api/report';

// Dynamic import for the Markdown editor to avoid SSR issues
const SimpleMDE = dynamic(() => import('react-simplemde-editor'), { ssr: false });

// Define Report interface
interface Report {
  id: number;
  template_id: number;
  title: string;
  content: string;
  formatted_file_path: string | null;
  created_at: string;
  updated_at: string | null;
  is_finalized: boolean;
}

const EditPage = () => {
  const router = useRouter();
  const { id } = router.query; // Get report ID from URL
  
  // State
  const [report, setReport] = useState<Report | null>(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [aiInstructions, setAiInstructions] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRefining, setIsRefining] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Fetch report data on component mount
  useEffect(() => {
    const fetchReport = async () => {
      if (!id) return;
      
      setIsLoading(true);
      try {
        // Call the API client function to fetch the report
        const reportData = await getReport(Number(id));
        setReport(reportData);
        setTitle(reportData.title);
        setContent(reportData.content);
      } catch (err) {
        console.error('Error fetching report:', err);
        setError('Failed to load report. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchReport();
  }, [id]);

  // Handle saving the edited report
  const handleSave = async () => {
    if (!report) return;
    
    setIsLoading(true);
    setError('');
    setSuccess('');
    
    try {
      // Call the API client function to update the report
      const updatedReport = await updateReport(report.id, {
        title,
        content,
        is_finalized: false
      });
      
      setReport(updatedReport);
      setSuccess('Report saved successfully!');
    } catch (err) {
      console.error('Error saving report:', err);
      setError('Failed to save report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  // Handle AI refinement
  const handleRefine = async () => {
    if (!report || !aiInstructions.trim()) return;
    
    setIsRefining(true);
    setError('');
    
    try {
      // Call the API client function for AI refinement
      const refinedReport = await refineReport(report.id, aiInstructions);
      
      setReport(refinedReport);
      setContent(refinedReport.content);
      setSuccess('Report refined successfully!');
      setAiInstructions(''); // Clear the instructions field
    } catch (err) {
      console.error('Error refining report:', err);
      setError('Failed to refine report. Please try again.');
    } finally {
      setIsRefining(false);
    }
  };
  
  // Handle report finalization
  const handleFinalize = async () => {
    if (!report) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      // Call the API client function to finalize the report
      const finalizedReport = await finalizeReport({
        report_id: report.id,
        template_id: 1  // Always use template ID 1
      });
      
      setSuccess('Report finalized successfully!');
      
      // Redirect to download page
      setTimeout(() => {
        router.push(`/download?id=${report.id}`);
      }, 1500);
    } catch (err) {
      console.error('Error finalizing report:', err);
      setError('Failed to finalize report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  // If loading or no report yet
  if (isLoading && !report) {
    return (
      <Container maxWidth="lg" sx={{ mt: 5, mb: 5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }
  
  return (
    <Container maxWidth="lg" sx={{ mt: 5, mb: 5 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Edit Report
      </Typography>
      
      {/* Report Editor */}
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <TextField
          label="Report Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          fullWidth
          variant="outlined"
          sx={{ mb: 3 }}
          disabled={report?.is_finalized}
        />
        
        <TextField
          label="Report Content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          fullWidth
          multiline
          rows={20}
          variant="outlined"
          sx={{ mb: 3, fontFamily: 'monospace' }}
          disabled={report?.is_finalized}
        />
        
        {/* Action buttons */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={handleSave}
            disabled={isLoading || report?.is_finalized}
          >
            {isLoading ? <CircularProgress size={24} /> : 'Save Changes'}
          </Button>
          
          <Button 
            variant="contained" 
            color="success" 
            onClick={handleFinalize}
            disabled={isLoading || report?.is_finalized}
          >
            {isLoading ? <CircularProgress size={24} /> : 'Finalize Report'}
          </Button>
        </Box>
      </Paper>
      
      {/* AI Refinement Section */}
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          AI Assistance
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Provide instructions on how you'd like the AI to refine your report.
        </Typography>
        
        <TextField
          label="Instructions for AI"
          placeholder="E.g., 'Add more details to the damages section' or 'Make the tone more formal'"
          value={aiInstructions}
          onChange={(e) => setAiInstructions(e.target.value)}
          fullWidth
          multiline
          rows={4}
          variant="outlined"
          sx={{ mb: 3 }}
          disabled={isRefining || report?.is_finalized}
        />
        
        <Button 
          variant="contained" 
          color="secondary" 
          onClick={handleRefine}
          disabled={isRefining || !aiInstructions.trim() || report?.is_finalized}
          fullWidth
        >
          {isRefining ? <CircularProgress size={24} /> : 'Refine with AI'}
        </Button>
      </Paper>
      
      {/* Status messages */}
      <Snackbar 
        open={!!error} 
        autoHideDuration={6000} 
        onClose={() => setError('')}
      >
        <Alert onClose={() => setError('')} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
      
      <Snackbar 
        open={!!success} 
        autoHideDuration={3000} 
        onClose={() => setSuccess('')}
      >
        <Alert onClose={() => setSuccess('')} severity="success" sx={{ width: '100%' }}>
          {success}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default EditPage; 