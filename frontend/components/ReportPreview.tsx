import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Paper, 
  TextField,
  Divider,
  Stack,
  CircularProgress,
  Alert,
  IconButton
} from '@mui/material';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import { formatReport } from '../api/format';
import { getReport } from '../api/report';
import { Report } from '../src/types';

interface Props {
  reportId: string | null;  // UUID
  onError?: (error: Error) => void;
}

const ReportPreview: React.FC<Props> = ({ reportId, onError }) => {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');

  useEffect(() => {
    if (reportId) {
      loadReport();
    }
  }, [reportId]);

  useEffect(() => {
    if (report?.content) {
      setEditedContent(report.content);
    }
  }, [report?.content]);

  const loadReport = async () => {
    try {
      setLoading(true);
      const reportData = await getReport(reportId as string) as Report;
      setReport(reportData);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load report';
      setError(errorMessage);
      if (onError) {
        onError(new Error(errorMessage));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    setEditing(true);
  };

  const handleSave = () => {
    if (!report) return;
    // TODO: Implement save functionality
    setEditing(false);
  };

  const handlePreview = async () => {
    if (!reportId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      await formatReport(reportId, true); // true = preview mode
    } catch (err) {
      console.error('Error generating preview:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate preview. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleFinalize = async () => {
    if (!reportId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      await formatReport(reportId, false); // false = final mode
    } catch (err) {
      console.error('Error finalizing report:', err);
      setError(err instanceof Error ? err.message : 'Failed to finalize report. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!report) {
    return null;
  }

  return (
    <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h5" gutterBottom>
        Report Preview & Editing
      </Typography>
      
      <Divider sx={{ my: 2 }} />
      
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
        <Typography variant="h6">Report Preview</Typography>
        <Box>
          {!editing ? (
            <IconButton onClick={handleEdit} color="primary">
              <EditIcon />
            </IconButton>
          ) : (
            <IconButton onClick={handleSave} color="primary">
              <SaveIcon />
            </IconButton>
          )}
        </Box>
      </Box>
      
      {loading ? (
        <CircularProgress />
      ) : error ? (
        <Typography color="error">{error}</Typography>
      ) : editing ? (
        <Box sx={{ mb: 3 }}>
          <TextField
            multiline
            fullWidth
            minRows={10}
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            variant="outlined"
          />
        </Box>
      ) : (
        <Box sx={{ mb: 3 }}>
          <Paper 
            elevation={0} 
            sx={{ 
              p: 2, 
              backgroundColor: '#f9f9f9',
              minHeight: '300px',
              whiteSpace: 'pre-wrap'
            }}
          >
            <Typography variant="body1">{report.content}</Typography>
          </Paper>
        </Box>
      )}
      
      <Divider sx={{ my: 2 }} />
      
      {error && (
        <Alert severity="error" sx={{ mt: 2, mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
        <Button
          variant="contained"
          color="secondary"
          onClick={handlePreview}
          disabled={loading || !reportId}
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PictureAsPdfIcon />}
        >
          Preview PDF
        </Button>
        
        <Button
          variant="contained"
          color="success"
          onClick={handleFinalize}
          disabled={loading || !reportId}
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PictureAsPdfIcon />}
        >
          Finalize Report
        </Button>
      </Stack>
    </Paper>
  );
};

export default ReportPreview; 