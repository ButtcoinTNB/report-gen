import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Paper, 
  CircularProgress,
  Alert,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import DeleteIcon from '@mui/icons-material/Delete';
import { uploadFile } from '../api/upload';

interface FileUploadProps {
  onUploadSuccess: (reportId: number) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Using a default template ID of 1, no dropdown needed
  const templateId = 1;

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      // Convert FileList to array and append to existing files
      const newFiles = Array.from(event.target.files);
      setFiles(prevFiles => [...prevFiles, ...newFiles]);
      setError(null);
    }
  };

  const handleRemoveFile = (index: number) => {
    setFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (files.length === 0) {
      setError('Please select at least one file to upload.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Call the API to upload the files
      const response = await uploadFile(files, templateId);
      console.log('Upload response received:', response);
      
      // Handle successful upload
      if (response && response.report_id) {
        console.log('Report ID received:', response.report_id);
        onUploadSuccess(response.report_id);
      } else {
        console.error('Missing report_id in response:', response);
        throw new Error('Invalid response from server: missing report_id');
      }
    } catch (err) {
      console.error('Error uploading files:', err);
      setError('Failed to upload files. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
      <form onSubmit={handleSubmit}>
        <Typography variant="h5" gutterBottom>
          Upload Case Documents
        </Typography>
        
        <Grid container spacing={3}>
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
                multiple // Allow multiple file selection
              />
              <CloudUploadIcon sx={{ fontSize: 60, color: '#1976d2', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Drag & Drop or Click to Upload
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Supported formats: PDF, Word, Text
              </Typography>
              <Typography variant="body2" color="primary" sx={{ mt: 1 }}>
                You can select multiple files
              </Typography>
            </Box>
          </Grid>
          
          {files.length > 0 && (
            <Grid item xs={12}>
              <Typography variant="subtitle1" gutterBottom>
                Selected Files ({files.length})
              </Typography>
              <List>
                {files.map((file, index) => (
                  <ListItem 
                    key={index}
                    secondaryAction={
                      <Button 
                        onClick={() => handleRemoveFile(index)}
                        color="error"
                        size="small"
                        startIcon={<DeleteIcon />}
                      >
                        Remove
                      </Button>
                    }
                  >
                    <ListItemIcon>
                      <InsertDriveFileIcon />
                    </ListItemIcon>
                    <ListItemText 
                      primary={file.name} 
                      secondary={`${(file.size / 1024).toFixed(2)} KB`} 
                    />
                  </ListItem>
                ))}
              </List>
            </Grid>
          )}
          
          <Grid item xs={12}>
            <Button
              variant="contained"
              size="large"
              type="submit"
              disabled={loading || files.length === 0}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
              fullWidth
            >
              {loading ? 'Uploading...' : `Upload ${files.length} Document${files.length !== 1 ? 's' : ''}`}
            </Button>
          </Grid>
          
          {error && (
            <Grid item xs={12}>
              <Alert severity="error">{error}</Alert>
            </Grid>
          )}
        </Grid>
      </form>
    </Paper>
  );
};

export default FileUpload; 