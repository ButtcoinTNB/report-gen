import React, { useState, useCallback } from 'react';
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
  ListItemIcon,
  IconButton,
  Chip
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import DeleteIcon from '@mui/icons-material/Delete';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import ImageIcon from '@mui/icons-material/Image';
import DescriptionIcon from '@mui/icons-material/Description';
import { uploadFile } from '../api/upload';
import { useDropzone } from 'react-dropzone';

interface FileUploadProps {
  onUploadSuccess: (reportId: number) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Using a default template ID of 1, no dropdown needed
  const templateId = 1;

  // Get icon based on file type
  const getFileIcon = (file: File) => {
    const type = file.type.split('/')[0];
    const extension = file.name.split('.').pop()?.toLowerCase();
    
    if (extension === 'pdf' || file.type === 'application/pdf') {
      return <PictureAsPdfIcon color="error" />;
    } else if (type === 'image') {
      return <ImageIcon color="primary" />;
    } else {
      return <DescriptionIcon color="action" />;
    }
  };

  // Get file size in readable format
  const getFileSize = (size: number) => {
    if (size < 1024) {
      return `${size} bytes`;
    } else if (size < 1024 * 1024) {
      return `${(size / 1024).toFixed(1)} KB`;
    } else {
      return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    }
  };
  
  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prevFiles => [...prevFiles, ...acceptedFiles]);
    setError(null);
  }, []);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg'],
      'text/plain': ['.txt'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    }
  });

  const handleRemoveFile = (index: number) => {
    setFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (files.length === 0) {
      setError("Please select at least one file to upload.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Create FormData object
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });
      formData.append('template_id', templateId.toString());

      const response = await uploadFile(formData);
      console.log("Upload response:", response);
      
      // Check for success
      if (response && response.report_id) {
        console.log("Upload success with report ID:", response.report_id);
        onUploadSuccess(response.report_id);
      } else {
        setError("No report ID received from the server.");
      }
    } catch (err) {
      console.error("Error uploading files:", err);
      setError("Failed to upload files. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ 
      p: 4, 
      mb: 4,
      borderRadius: 3,
      background: 'linear-gradient(145deg, rgba(255,255,255,1) 0%, rgba(249,249,252,1) 100%)'
    }}>
      <Box component="form" onSubmit={handleSubmit} noValidate>
        <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
          Upload Documents
        </Typography>
        
        <Box
          {...getRootProps()}
          sx={{
            border: '1px dashed',
            borderColor: isDragActive ? 'primary.main' : 'grey.300',
            borderRadius: 2,
            p: 3,
            textAlign: 'center',
            cursor: 'pointer',
            mb: 3,
            backgroundColor: isDragActive ? 'rgba(0, 113, 227, 0.05)' : 'transparent',
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              borderColor: 'primary.main',
              backgroundColor: 'rgba(0, 113, 227, 0.05)'
            }
          }}
        >
          <input {...getInputProps()} />
          <CloudUploadIcon fontSize="large" color="primary" sx={{ mb: 2, fontSize: 45 }} />
          <Typography variant="h6" gutterBottom>
            {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            or click to browse your device
          </Typography>
          <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 1 }}>
            Supports PDF, DOC, DOCX, TXT, and image files
          </Typography>
        </Box>
        
        {files.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Selected Files ({files.length})
            </Typography>
            <Paper variant="outlined" sx={{ maxHeight: 240, overflow: 'auto', borderRadius: 2 }}>
              <List dense disablePadding>
                {files.map((file, index) => (
                  <ListItem
                    key={index}
                    secondaryAction={
                      <IconButton edge="end" aria-label="delete" onClick={() => handleRemoveFile(index)} size="small">
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    }
                    sx={{ 
                      borderBottom: index < files.length - 1 ? '1px solid' : 'none',
                      borderColor: 'divider',
                      py: 1
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      {getFileIcon(file)}
                    </ListItemIcon>
                    <ListItemText 
                      primary={file.name} 
                      secondary={getFileSize(file.size)}
                      primaryTypographyProps={{ 
                        variant: 'body2', 
                        sx: { 
                          fontWeight: 500,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        } 
                      }}
                      secondaryTypographyProps={{ 
                        variant: 'caption'
                      }}
                    />
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Box>
        )}
        
        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {error}
          </Alert>
        )}
        
        <Button
          type="submit"
          variant="contained"
          color="primary"
          size="large"
          fullWidth
          disabled={loading || files.length === 0}
          sx={{ 
            py: 1.5,
            position: 'relative',
            fontWeight: 500
          }}
        >
          {loading ? (
            <>
              <CircularProgress 
                size={24} 
                color="inherit" 
                sx={{ 
                  position: 'absolute',
                  left: 'calc(50% - 12px)'
                }} 
              />
              <span style={{ opacity: 0 }}>Processing...</span>
            </>
          ) : files.length > 0 ? 'Upload and Generate Report' : 'Select Files to Upload'}
        </Button>
      </Box>
    </Paper>
  );
};

export default FileUpload; 