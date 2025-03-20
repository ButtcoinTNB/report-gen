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
import { generateApi, editApi, formatApi } from '../src/services';
import { 
  Report, 
  ReportDataCamel, 
  adaptReportData,
  EditReportResponseCamel,
  adaptEditReportResponse 
} from '../src/types';
import { logger } from '../src/utils/logger';
import { adaptApiResponse } from '../src/utils/adapters';

// Dynamic import for the Markdown editor to avoid SSR issues
const SimpleMDE = dynamic(() => import('react-simplemde-editor'), { ssr: false });

// Using the new camelCase interface
const EditPage = () => {
  const router = useRouter();
  const { id } = router.query;
  const [report, setReport] = useState<ReportDataCamel | null>(null);
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
      const reportData = await generateApi.getReport(reportId);
      
      // Convert to camelCase
      const camelReport = adaptReportData(reportData);
      
      setReport(camelReport);
      setTitle(camelReport.title || '');
      setContent(camelReport.content || '');
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
      await editApi.editReport(report.reportId, `Update the report with title: "${title}" and content: "${content}"`);
      
      const updatedReport = await generateApi.getReport(report.reportId);
      
      // Convert to camelCase
      const camelReport = adaptReportData(updatedReport);
      
      setReport(camelReport);
      setSuccess('Report saved successfully!');
    } catch (err) {
      logger.error('Error saving report:', err);
      setError(err instanceof Error ? err.message : 'Failed to save report. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleRefine = async () => {
    if (!report) return;

    try {
      setIsRefining(true);
      setError('');
      
      // Use the edit API that returns EditReportResponseCamel
      const result = await editApi.editReport(report.reportId, aiInstructions);
      
      // Get the updated report data after editing
      const updatedReport = await generateApi.getReport(report.reportId);
      const camelReport = adaptReportData(updatedReport);
      
      setReport(camelReport);
      setAiInstructions('');
    } catch (err) {
      logger.error('Error refining report:', err);
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
      await formatApi.formatReport(report.reportId, { previewMode: false });
      
      setSuccess('Report finalized successfully!');
      
      setTimeout(() => {
        router.push(`/download?id=${report.reportId}`);
      }, 1500);
    } catch (err) {
      logger.error('Error finalizing report:', err);
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
          disabled={report?.isFinalized}
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
          disabled={report?.isFinalized}
        />
        
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={handleSave}
            disabled={loading || report?.isFinalized}
          >
            {loading ? <CircularProgress size={24} /> : 'Salva Modifiche'}
          </Button>
          
          <Button 
            variant="contained" 
            color="success" 
            onClick={handleFinalize}
            disabled={loading || report?.isFinalized}
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
          disabled={isRefining || report?.isFinalized}
        />
        
        <Button 
          variant="contained" 
          color="secondary" 
          onClick={handleRefine}
          disabled={isRefining || !aiInstructions || report?.isFinalized}
          sx={{ width: '100%' }}
        >
          {isRefining ? (
            <>
              <CircularProgress size={24} sx={{ mr: 1 }} color="inherit" />
              Refining Report...
            </>
          ) : 'Refine with AI'}
        </Button>
      </Paper>
      
      {error && (
        <Snackbar open={!!error} autoHideDuration={6000} onClose={() => setError(null)}>
          <Alert onClose={() => setError(null)} severity="error" sx={{ width: '100%' }}>
            {error}
          </Alert>
        </Snackbar>
      )}
      
      {success && (
        <Snackbar open={!!success} autoHideDuration={3000} onClose={() => setSuccess('')}>
          <Alert onClose={() => setSuccess('')} severity="success" sx={{ width: '100%' }}>
            {success}
          </Alert>
        </Snackbar>
      )}
    </Container>
  );
};

export default EditPage; 