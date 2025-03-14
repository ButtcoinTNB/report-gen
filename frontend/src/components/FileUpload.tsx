import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Paper, 
  CircularProgress,
  Alert,
  AlertTitle,
  Grid,
  TextField
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { uploadFile } from '@/api/upload';

interface FileUploadProps {
  onUploadSuccess: (reportId: number) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState<number>(1); // Default template ID
  const [fileName, setFileName] = useState<string>('');

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const selectedFile = event.target.files[0];
      setFile(selectedFile);
      setFileName(selectedFile.name);
      setError(null);
    }
  };

  const handleSubmit = async () => {
    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Call the API to upload the file
      const response = await uploadFile(file, templateId);
      
      // Handle successful upload
      if (response && response.report_id) {
        onUploadSuccess(response.report_id);
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (err) {
      console.error('Error uploading file:', err);
      setError('Failed to upload file. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h5" gutterBottom>
        Upload Case Documents
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            type="number"
            label="Template ID"
            value={templateId}
            onChange={(e) => setTemplateId(Number(e.target.value))}
            margin="normal"
            InputProps={{ inputProps: { min: 1 } }}
          />
        </Grid>
        
        <Grid item xs={12}>
          <Box 
            sx={{ 
              border: '2px dashed #ccc', 
              borderRadius: 2, 
              p: 3, 
              textAlign: 'center',
              cursor: 'pointer',
              '&:hover': { borderColor: '#1976d2' } 
            }}
            onClick={() => document.getElementById('file-upload')?.click()}
          >
            <input
              type="file"
              id="file-upload"
              style={{ display: 'none' }}
              onChange={handleFileChange}
              accept=".pdf,.doc,.docx,.txt"
            />
            <CloudUploadIcon sx={{ fontSize: 60, color: '#1976d2', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Drag & Drop or Click to Upload
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Supported formats: PDF, Word, Text
            </Typography>
            {fileName && (
              <Typography variant="body1" sx={{ mt: 2 }}>
                Selected: {fileName}
              </Typography>
            )}
          </Box>
        </Grid>
        
        <Grid item xs={12}>
          <Button
            variant="contained"
            size="large"
            onClick={handleSubmit}
            disabled={loading || !file}
            startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
            fullWidth
          >
            {loading ? 'Uploading...' : 'Upload Document'}
          </Button>
        </Grid>
        
        {error && (
          <Grid item xs={12}>
            <Alert severity="error">
              <AlertTitle>Error</AlertTitle>
              {error}
            </Alert>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
};

export default FileUpload; 