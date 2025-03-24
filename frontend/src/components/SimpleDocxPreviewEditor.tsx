import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  CircularProgress,
  Divider,
  IconButton,
  Tooltip,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent
} from '@mui/material';
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Visibility as ViewIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  History as HistoryIcon
} from '@mui/icons-material';
import { useTask } from '../context/TaskContext';
import reportService from '../services/ReportService';

interface SimpleDocxPreviewEditorProps {
  reportId: string;
  onRefine?: (instructions: string) => Promise<boolean>;
  onVersionSelect?: (versionId: string) => void;
  readOnly?: boolean;
}

const SimpleDocxPreviewEditor: React.FC<SimpleDocxPreviewEditorProps> = ({
  reportId,
  onRefine,
  onVersionSelect,
  readOnly = false
}) => {
  const { task, transitionToStage, downloadVersion } = useTask();
  const [loading, setLoading] = useState(true);
  const [documentContent, setDocumentContent] = useState<string>('');
  const [refinementInstructions, setRefinementInstructions] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [selectedVersionId, setSelectedVersionId] = useState<string>('');

  // Load document content
  useEffect(() => {
    const loadDocument = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // If a version is selected, use that, otherwise get the latest
        const versionId = selectedVersionId || task.currentVersionId;
        
        if (!versionId) {
          throw new Error('No version ID available');
        }
        
        const versionData = await reportService.getVersion(versionId);
        setDocumentContent(versionData.content);
      } catch (err) {
        console.error('Failed to load document:', err);
        setError('Failed to load document. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    
    loadDocument();
  }, [reportId, selectedVersionId, task.currentVersionId]);

  // Handle refinement submission
  const handleRefineSubmit = async () => {
    if (!refinementInstructions.trim()) {
      setError('Please enter refinement instructions.');
      return;
    }
    
    setSubmitting(true);
    setError(null);
    
    try {
      if (onRefine) {
        const success = await onRefine(refinementInstructions);
        if (success) {
          setRefinementInstructions('');
          transitionToStage('formatting');
        }
      } else {
        // Use service directly if no callback provided
        await reportService.refineReport(reportId, refinementInstructions);
        setRefinementInstructions('');
        transitionToStage('formatting');
      }
    } catch (err) {
      console.error('Refinement failed:', err);
      setError('Failed to submit refinement request. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle version selection
  const handleVersionChange = (event: SelectChangeEvent<string>) => {
    const versionId = event.target.value;
    setSelectedVersionId(versionId);
    
    if (onVersionSelect) {
      onVersionSelect(versionId);
    }
  };

  // Handle document download
  const handleDownload = async () => {
    const versionId = selectedVersionId || task.currentVersionId;
    if (!versionId) {
      setError('No version available to download');
      return;
    }
    
    try {
      await downloadVersion(versionId);
    } catch (err) {
      console.error('Download failed:', err);
      setError('Failed to download document. Please try again.');
    }
  };

  // Toggle edit mode
  const toggleEditMode = () => {
    if (readOnly) return;
    setEditMode(!editMode);
  };

  // Save edited content
  const handleSaveEdit = async () => {
    // Implementation would depend on how you want to handle direct edits
    // This might create a new version or update the current one
    setEditMode(false);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">
          {editMode ? 'Edit Document' : 'Document Preview'}
        </Typography>
        
        <Box>
          {task.versions && task.versions.length > 0 && (
            <FormControl sx={{ minWidth: 200, mr: 2 }} size="small">
              <InputLabel id="version-select-label">Version</InputLabel>
              <Select
                labelId="version-select-label"
                value={selectedVersionId || task.currentVersionId || ''}
                label="Version"
                onChange={handleVersionChange}
              >
                {task.versions.map(version => (
                  <MenuItem key={version.id} value={version.id}>
                    {version.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          
          <Tooltip title={editMode ? 'View mode' : 'Edit mode'}>
            <IconButton 
              onClick={toggleEditMode}
              disabled={readOnly}
              color={editMode ? 'primary' : 'default'}
            >
              {editMode ? <ViewIcon /> : <EditIcon />}
            </IconButton>
          </Tooltip>
          
          {editMode && (
            <Tooltip title="Save changes">
              <IconButton 
                onClick={handleSaveEdit}
                color="primary"
              >
                <SaveIcon />
              </IconButton>
            </Tooltip>
          )}
          
          <Tooltip title="Download document">
            <IconButton onClick={handleDownload}>
              <DownloadIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="View version history">
            <IconButton onClick={() => {}}>
              <HistoryIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>
      
      <Paper 
        elevation={2} 
        sx={{ 
          p: 3, 
          mb: 3, 
          minHeight: '50vh',
          maxHeight: '60vh',
          overflow: 'auto',
          whiteSpace: 'pre-wrap',
          backgroundColor: '#fff',
          fontFamily: editMode ? 'inherit' : '"Times New Roman", serif',
          fontSize: editMode ? 'inherit' : '1rem',
          lineHeight: editMode ? 'inherit' : 1.5
        }}
      >
        {editMode ? (
          <TextField
            multiline
            fullWidth
            variant="outlined"
            value={documentContent}
            onChange={(e) => setDocumentContent(e.target.value)}
            sx={{ '& .MuiOutlinedInput-root': { p: 0 } }}
            InputProps={{
              style: { fontSize: '1rem', lineHeight: 1.5 }
            }}
          />
        ) : (
          <div dangerouslySetInnerHTML={{ __html: documentContent }} />
        )}
      </Paper>
      
      {task.stage === 'refinement' && !readOnly && (
        <>
          <Divider sx={{ mb: 3 }} />
          
          <Typography variant="h6" sx={{ mb: 2 }}>
            Refinement Instructions
          </Typography>
          
          <TextField
            multiline
            fullWidth
            rows={4}
            variant="outlined"
            placeholder="Enter your instructions to refine the document. Be specific about what needs to be changed or improved."
            value={refinementInstructions}
            onChange={(e) => setRefinementInstructions(e.target.value)}
            disabled={submitting}
            sx={{ mb: 2 }}
          />
          
          <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleRefineSubmit}
              disabled={submitting || !refinementInstructions.trim()}
              startIcon={submitting ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />}
            >
              {submitting ? 'Submitting...' : 'Submit Refinement'}
            </Button>
          </Box>
        </>
      )}
    </Box>
  );
};

export default SimpleDocxPreviewEditor; 