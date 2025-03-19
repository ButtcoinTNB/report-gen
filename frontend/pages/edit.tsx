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
import { Report } from '../src/types';

// Dynamic import for the Markdown editor to avoid SSR issues
const SimpleMDE = dynamic(() => import('react-simplemde-editor'), { ssr: false });

interface ReportData {
    report_id: string;  // UUID
    template_id?: string;  // UUID
    title?: string;
    content?: string;
    is_finalized?: boolean;
    files_cleaned?: boolean;
    created_at?: string;
    updated_at?: string;
}

const EditPage = () => {
  const router = useRouter();
  const { id } = router.query;
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aiInstructions, setAiInstructions] = useState('');
  const [isRefining, setIsRefining] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (id) {
      loadReport(id as string);
    }
  }, [id]);

  const loadReport = async (reportId: string) => {
    try {
      setLoading(true);
      const reportData = await getReport(reportId) as Report;
      setReport({
        report_id: reportData.report_id,
        template_id: reportData.template_id,
        title: reportData.title,
        content: reportData.content,
        is_finalized: reportData.is_finalized,
        files_cleaned: reportData.files_cleaned,
        created_at: reportData.created_at,
        updated_at: reportData.updated_at
      });
      setTitle(reportData.title || '');
      setContent(reportData.content || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!report) return;
    
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const updatedReport = await updateReport(report.report_id, {
        title,
        content,
        is_finalized: false
      }) as Report;
      
      setReport(updatedReport);
      setSuccess('Report saved successfully!');
    } catch (err) {
      console.error('Error saving report:', err);
      setError(err instanceof Error ? err.message : 'Failed to save report. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleRefine = async () => {
    if (!report) return;

    try {
      setIsRefining(true);
      const refinedReport = await refineReport(report.report_id, aiInstructions) as Report;
      setReport({
        report_id: refinedReport.report_id,
        template_id: refinedReport.template_id,
        title: refinedReport.title,
        content: refinedReport.content,
        is_finalized: refinedReport.is_finalized,
        files_cleaned: refinedReport.files_cleaned,
        created_at: refinedReport.created_at,
        updated_at: refinedReport.updated_at
      });
      setAiInstructions('');
    } catch (err) {
      console.error('Error refining report:', err);
      setError(err instanceof Error ? err.message : 'Failed to refine report');
    } finally {
      setIsRefining(false);
    }
  };
  
  const handleFinalize = async () => {
    if (!report) return;
    
    setLoading(true);
    setError('');
    
    try {
      await finalizeReport({
        report_id: report.report_id,
        template_id: 1  // Always use template ID 1
      });
      
      setSuccess('Report finalized successfully!');
      
      setTimeout(() => {
        router.push(`/download?id=${report.report_id}`);
      }, 1500);
    } catch (err) {
      console.error('Error finalizing report:', err);
      setError(err instanceof Error ? err.message : 'Impossibile finalizzare il report. Riprova.');
    } finally {
      setLoading(false);
    }
  };
  
  if (loading && !report) {
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
        Modifica Report
      </Typography>
      
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <TextField
          label="Titolo del Report"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          fullWidth
          variant="outlined"
          sx={{ mb: 3 }}
          disabled={report?.is_finalized}
        />
        
        <TextField
          label="Contenuto del Report"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          fullWidth
          multiline
          rows={20}
          variant="outlined"
          sx={{ mb: 3, fontFamily: 'monospace' }}
          disabled={report?.is_finalized}
        />
        
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={handleSave}
            disabled={loading || report?.is_finalized}
          >
            {loading ? <CircularProgress size={24} /> : 'Salva Modifiche'}
          </Button>
          
          <Button 
            variant="contained" 
            color="success" 
            onClick={handleFinalize}
            disabled={loading || report?.is_finalized}
          >
            {loading ? <CircularProgress size={24} /> : 'Finalizza Report'}
          </Button>
        </Box>
      </Paper>
      
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Assistenza AI
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Fornisci istruzioni su come vorresti che l'AI perfezionasse il tuo report.
        </Typography>
        
        <TextField
          label="Istruzioni per l'AI"
          placeholder="Es., 'Aggiungi più dettagli alla sezione danni' o 'Rendi il tono più formale'"
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
          {isRefining ? <CircularProgress size={24} /> : 'Raffina con AI'}
        </Button>
      </Paper>
      
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