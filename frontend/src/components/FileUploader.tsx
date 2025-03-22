import React, { useCallback, useState, useEffect } from 'react';
import { useDropzone, FileWithPath } from 'react-dropzone';
import { Box, Typography, Paper, Button, Chip } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import CloudDoneIcon from '@mui/icons-material/CloudDone';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { 
  setLoading, 
  setDocumentIds, 
  setReportId, 
  setError,
  setActiveStep,
  setBackgroundUpload
} from '../store/reportSlice';
import { config } from '../../config';
import { UploadService, CHUNKED_UPLOAD_SIZE_THRESHOLD } from '../services/api/UploadService';

// Initialize upload service
const uploadService = new UploadService();

// This is a reusable file uploader component that uses Redux for state management
const FileUploader: React.FC = () => {
  const dispatch = useAppDispatch();
  const loading = useAppSelector(state => state.report.loading);
  const activeStep = useAppSelector(state => state.report.activeStep);
  const error = useAppSelector(state => state.report.error);
  const backgroundUpload = useAppSelector(state => state.report.backgroundUpload);
  const [filesSelected, setFilesSelected] = useState<FileWithPath[]>([]);

  // Handle file upload
  const handleUpload = useCallback(async (files: FileWithPath[]) => {
    if (!files || files.length === 0) {
      dispatch(setError('No files selected'));
      return;
    }

    // Save files for later use
    setFilesSelected(files);

    try {
      // Set loading state
      dispatch(setLoading({ 
        isLoading: true, 
        stage: 'uploading', 
        progress: 0,
        message: 'Uploading documents in background...' 
      }));

      // Start background upload
      dispatch(setBackgroundUpload({
        isUploading: true,
        totalFiles: files.length,
        uploadedFiles: 0,
        progress: 0
      }));

      // Move to next step immediately after initiating the upload
      dispatch(setActiveStep(activeStep + 1));

      // Use the UploadService to handle the upload (including chunked upload for large files)
      const result = await uploadService.uploadFiles(
        files as File[], // Cast to File[] as FileWithPath extends File
        (progress) => {
          // Update progress in the UI
          dispatch(setBackgroundUpload({
            progress,
            uploadedFiles: Math.floor((files.length * progress) / 100)
          }));
        }
      );

      // Update progress to complete
      dispatch(setLoading({ progress: 100 }));
      
      // Get the document IDs and report ID from the result
      dispatch(setDocumentIds(result.fileCount ? Array(result.fileCount).fill(result.reportId) : [result.reportId]));
      dispatch(setReportId(result.reportId));

      // Complete loading and background upload
      dispatch(setLoading({ 
        isLoading: false, 
        progress: 100, 
        stage: 'complete',
        message: 'Upload complete!'
      }));

      dispatch(setBackgroundUpload({
        isUploading: false,
        progress: 100,
        uploadedFiles: files.length
      }));

    } catch (err) {
      // Handle errors
      console.error('Upload error:', err);
      dispatch(setError(err instanceof Error ? err.message : 'Upload failed'));
      dispatch(setLoading({ 
        isLoading: false,
        stage: 'error'
      }));
      dispatch(setBackgroundUpload({
        isUploading: false,
        error: err instanceof Error ? err.message : 'Upload failed'
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
      
      {filesSelected.length > 0 && (
        <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
          {filesSelected.map((file, index) => (
            <Chip 
              key={index}
              label={file.name}
              size="small"
              icon={backgroundUpload?.isUploading ? <CloudUploadIcon /> : <CloudDoneIcon />}
              color={backgroundUpload?.error ? "error" : "default"}
            />
          ))}
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
      
      {backgroundUpload?.isUploading && (
        <Typography variant="caption" color="primary" sx={{ mt: 1 }}>
          Files will be uploaded in the background while you proceed
        </Typography>
      )}
    </Paper>
  );
};

export default FileUploader; 