import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Paper, 
  TextField,
  Divider,
  Stack,
  CircularProgress
} from '@mui/material';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import { formatReport } from '../api/format';

interface ReportPreviewProps {
  reportId: number | null;
  reportText: string | null;
  onReportUpdated: (text: string) => void;
  onPreviewReady: () => void;
}

const ReportPreview: React.FC<ReportPreviewProps> = ({
  reportId,
  reportText,
  onReportUpdated,
  onPreviewReady
}) => {
  const [editing, setEditing] = useState(false);
  const [editedText, setEditedText] = useState(reportText || '');
  const [loading, setLoading] = useState(false);

  // Update editedText when reportText changes (like when a new report is generated)
  React.useEffect(() => {
    if (reportText) {
      setEditedText(reportText);
    }
  }, [reportText]);

  const handleEdit = () => {
    setEditing(true);
  };

  const handleSave = () => {
    onReportUpdated(editedText);
    setEditing(false);
  };

  const handlePreview = async () => {
    if (!reportId) return;
    
    setLoading(true);
    try {
      await formatReport(reportId, true); // true = preview mode
      onPreviewReady();
    } catch (error) {
      console.error('Error generating preview:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFinalize = async () => {
    if (!reportId) return;
    
    setLoading(true);
    try {
      await formatReport(reportId, false); // false = final mode
      onPreviewReady();
    } catch (error) {
      console.error('Error finalizing report:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!reportText) {
    return null;
  }

  return (
    <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h5" gutterBottom>
        Report Preview & Editing
      </Typography>
      
      <Divider sx={{ my: 2 }} />
      
      {editing ? (
        <Box sx={{ mb: 3 }}>
          <TextField
            multiline
            fullWidth
            minRows={10}
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            variant="outlined"
          />
          <Button
            variant="contained"
            color="primary"
            onClick={handleSave}
            startIcon={<SaveIcon />}
            sx={{ mt: 2 }}
          >
            Save Changes
          </Button>
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
            <Typography variant="body1">{reportText}</Typography>
          </Paper>
          
          <Button
            variant="outlined"
            color="primary"
            onClick={handleEdit}
            startIcon={<EditIcon />}
            sx={{ mt: 2 }}
          >
            Edit Report
          </Button>
        </Box>
      )}
      
      <Divider sx={{ my: 2 }} />
      
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