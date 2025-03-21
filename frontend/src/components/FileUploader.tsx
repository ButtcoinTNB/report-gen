import React, { useCallback } from 'react';
import { useDropzone, FileWithPath } from 'react-dropzone';
import { Box, Typography, Paper, Button } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { 
  setLoading, 
  setDocumentIds, 
  setReportId, 
  setError,
  setActiveStep
} from '../store/reportSlice';
import { config } from '../../config';

// This is a reusable file uploader component that uses Redux for state management
const FileUploader: React.FC = () => {
  const dispatch = useAppDispatch();
  const loading = useAppSelector(state => state.report.loading);
  const activeStep = useAppSelector(state => state.report.activeStep);
  const error = useAppSelector(state => state.report.error);

  // Handle file upload
  const handleUpload = useCallback(async (files: FileWithPath[]) => {
    if (!files || files.length === 0) {
      dispatch(setError('No files selected'));
      return;
    }

    try {
      // Set loading state
      dispatch(setLoading({ 
        isLoading: true, 
        stage: 'uploading', 
        progress: 0,
        message: 'Uploading documents...' 
      }));

      // Create form data for upload
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });

      // Call API to upload files
      const response = await fetch(`${config.API_URL}/api/upload/documents`, {
        method: 'POST',
        body: formData
      });

      // Handle response
      const data = await response.json();
      
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || `Upload failed with status ${response.status}`);
      }

      // Update progress to complete
      dispatch(setLoading({ progress: 100 }));
      
      // Get the document IDs from the response
      const documentIds = data.data?.document_ids || 
                         data.data?.documentIds || 
                         (Array.isArray(data.data) ? data.data : []);
      
      // Update state with document IDs
      dispatch(setDocumentIds(documentIds));
      
      // Get the report ID if present
      if (data.data?.report_id || data.data?.reportId) {
        dispatch(setReportId(data.data?.report_id || data.data?.reportId));
      }

      // Complete loading
      dispatch(setLoading({ 
        isLoading: false, 
        progress: 100, 
        stage: 'complete',
        message: 'Upload complete!'
      }));

      // Move to next step after a short delay to show the completion state
      setTimeout(() => {
        dispatch(setActiveStep(activeStep + 1));
      }, 500);
    } catch (err) {
      // Handle errors
      console.error('Upload error:', err);
      dispatch(setError(err instanceof Error ? err.message : 'Upload failed'));
      dispatch(setLoading({ 
        isLoading: false,
        stage: 'error'
      }));
    }
  }, [dispatch, activeStep]);

  // Set up react-dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleUpload,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt']
    }
  });

  return (
    <Paper
      {...getRootProps()}
      elevation={2}
      sx={{
        p: 4,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
        border: '2px dashed',
        borderColor: isDragActive ? 'primary.main' : 'divider',
        borderRadius: 2,
        cursor: loading.isLoading ? 'default' : 'pointer',
        position: 'relative',
        minHeight: 200,
        transition: 'all 0.2s ease-in-out'
      }}
    >
      <input {...getInputProps()} disabled={loading.isLoading} />
      
      <UploadFileIcon color="primary" sx={{ fontSize: 48, mb: 2 }} />
      
      <Typography variant="h6" gutterBottom align="center">
        {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
      </Typography>
      
      <Typography variant="body2" color="textSecondary" align="center">
        Or click to select files
      </Typography>
      
      <Typography variant="caption" color="textSecondary" sx={{ mt: 1 }} align="center">
        Supported formats: PDF, DOCX, DOC, TXT
      </Typography>
      
      {error && (
        <Typography color="error" sx={{ mt: 2 }} align="center">
          {error}
        </Typography>
      )}
      
      {loading.isLoading && (
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Typography variant="body2" sx={{ mb: 1 }}>
            {loading.message || 'Processing...'}
          </Typography>
          <Box sx={{ 
            width: '100%', 
            height: 4, 
            bgcolor: 'grey.200', 
            borderRadius: 1,
            overflow: 'hidden'
          }}>
            <Box 
              sx={{ 
                width: `${loading.progress}%`, 
                height: '100%', 
                bgcolor: 'primary.main',
                transition: 'width 0.3s ease-in-out'
              }} 
            />
          </Box>
        </Box>
      )}
      
      <Button 
        variant="contained" 
        color="primary" 
        sx={{ mt: 2 }}
        disabled={loading.isLoading}
        onClick={(e) => {
          e.stopPropagation();
          (document.querySelector('input[type="file"]') as HTMLInputElement)?.click();
        }}
      >
        {loading.isLoading ? 'Uploading...' : 'Select Files'}
      </Button>
    </Paper>
  );
};

export default FileUploader; 