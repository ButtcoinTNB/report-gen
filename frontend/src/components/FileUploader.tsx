import React, { useCallback, useState, useEffect } from 'react';
import { useDropzone, FileWithPath } from 'react-dropzone';
import { Box, Typography, Paper, Button, Chip, Alert, LinearProgress, CircularProgress } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import CloudDoneIcon from '@mui/icons-material/CloudDone';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import WarningIcon from '@mui/icons-material/Warning';
import ReplayIcon from '@mui/icons-material/Replay';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { 
  setLoading, 
  setDocumentIds, 
  setReportId, 
  setError,
  setBackgroundUpload,
  setActiveStep
} from '../store/reportSlice';
import { UploadService, CHUNKED_UPLOAD_SIZE_THRESHOLD } from '../services/api/UploadService';
import { logger } from '../utils/logger';
import UploadProgressTracker from './UploadProgressTracker';
import { formatErrorForUser } from '../utils/errorHandler';
import { generateUUID } from '../utils/common';

// Define the FileUploader props interface
export interface FileUploaderProps {
  reportId?: string;
  maxFiles?: number;
  maxFileSize?: number;
  acceptedFileTypes?: Record<string, string[]>;
  allowContinueWhileUploading?: boolean;
}

// Initialize upload service
const uploadService = new UploadService();

// Maximum retry attempts for failed uploads
const MAX_RETRIES = 3;

// This is a reusable file uploader component that uses Redux for state management
const FileUploader: React.FC<FileUploaderProps> = ({
  reportId,
  maxFiles = 10,
  maxFileSize = 100 * 1024 * 1024, // 100MB default
  acceptedFileTypes = {
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'text/plain': ['.txt']
  },
  allowContinueWhileUploading = true
}) => {
  const dispatch = useAppDispatch();
  const loading = useAppSelector(state => state.report.loading);
  const storeReportId = useAppSelector(state => state.report.reportId);
  const backgroundUpload = useAppSelector(state => state.report.backgroundUpload);
  const [filesSelected, setFilesSelected] = useState<File[]>([]);
  const [uploadErrors, setUploadErrors] = useState<{file: string, error: string, retryable: boolean}[]>([]);
  const [retrying, setRetrying] = useState(false);
  const [canContinue, setCanContinue] = useState(false);
  
  // Use reportId from props or from store
  const effectiveReportId = reportId || storeReportId;

  // Handle file upload with retry logic
  const handleUpload = useCallback(async (files: FileWithPath[]) => {
    if (!files || files.length === 0) {
      return;
    }

    // Clear previous errors
    setUploadErrors([]);
    setFilesSelected(Array.from(files));
    setCanContinue(false);

    // Start loading and background upload
    dispatch(setLoading({ 
      isLoading: true, 
      progress: 0, 
      stage: 'uploading',
      message: 'Uploading files...'
    }));

    dispatch(setBackgroundUpload({
      isUploading: true,
      progress: 0,
      totalFiles: files.length,
      uploadedFiles: 0,
      error: null,
      uploadStartTime: Date.now(),
      uploadSessionId: generateUUID()
    }));

    try {
      // Keep track of uploaded document IDs
      const newDocumentIds: string[] = [];
      const fileErrors: {file: string, error: string, retryable: boolean}[] = [];

      // Create a new report if needed
      let currentReportId = effectiveReportId;
      if (!currentReportId) {
        try {
          currentReportId = await uploadService.createReport();
          dispatch(setReportId(currentReportId));
        } catch (error) {
          logger.error('Failed to create report:', error);
          throw new Error('Failed to create report');
        }
      }

      // Enable continue button after the first file starts uploading (if allowed)
      if (allowContinueWhileUploading) {
        setCanContinue(true);
      }

      // Process each file sequentially
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        try {
          // Check file size
          if (file.size > maxFileSize) {
            fileErrors.push({
              file: file.name,
              error: `File troppo grande (${Math.round(file.size/1024/1024)}MB). Dimensione massima: ${Math.round(maxFileSize/1024/1024)}MB`,
              retryable: false
            });
            continue;
          }

          // Try to upload with retries
          let documentId = '';
          let attempt = 1;
          let success = false;
          
          while (attempt <= MAX_RETRIES && !success) {
            try {
              logger.info(`Uploading file ${file.name} (attempt ${attempt}/${MAX_RETRIES})`);
              
              // Progress callback for this file
              const onProgress = (progress: number) => {
                const overallProgress = Math.floor(((i * 100) + progress) / files.length);
                dispatch(setBackgroundUpload({
                  isUploading: true,
                  progress: overallProgress,
                  uploadedFiles: progress === 100 ? (backgroundUpload?.uploadedFiles || 0) + 1 : backgroundUpload?.uploadedFiles,
                }));
              };
              
              // Use the appropriate upload method
              const response = await uploadService.uploadSingleFile(file, currentReportId, onProgress);
              documentId = response.reportId;
              success = true;
            } catch (error) {
              logger.error(`Failed to upload ${file.name} (attempt ${attempt}/${MAX_RETRIES}):`, error);
              
              // If we haven't exceeded max retries, wait with exponential backoff
              if (attempt < MAX_RETRIES) {
                const backoffTime = Math.pow(2, attempt) * 1000; // exponential backoff
                await new Promise(resolve => setTimeout(resolve, backoffTime));
                attempt++;
              } else {
                throw error; // Let outer catch handle it
              }
            }
          }
          
          if (success && documentId) {
            newDocumentIds.push(documentId);
          }
        } catch (error) {
          // Add to errors array
          const errorMessage = error instanceof Error 
            ? error.message
            : 'Errore sconosciuto durante il caricamento';
          
          fileErrors.push({
            file: file.name,
            error: errorMessage,
            retryable: true // Assume most errors are retryable
          });
        }
      }

      // Update upload errors if any
      if (fileErrors.length > 0) {
        setUploadErrors(fileErrors);
        
        // If all files failed, throw an error
        if (fileErrors.length === files.length) {
          throw new Error('Tutti i file non sono stati caricati');
        }
      }

      // Set document IDs for successfully uploaded files
      if (newDocumentIds.length > 0) {
        dispatch(setDocumentIds(newDocumentIds));
      }

      // Complete loading
      dispatch(setLoading({ 
        isLoading: false, 
        progress: 100, 
        stage: 'complete',
        message: 'Upload complete!'
      }));

      // Update background upload state
      dispatch(setBackgroundUpload({
        isUploading: fileErrors.length > 0, // Still consider uploading if there are errors (for retry)
        progress: 100,
        uploadedFiles: newDocumentIds.length,
        error: fileErrors.length > 0 ? `${fileErrors.length} file non caricati` : null
      }));

      // Allow continue if any files were uploaded successfully
      setCanContinue(newDocumentIds.length > 0);

    } catch (error) {
      // Handle errors
      logger.error('Upload error:', error);
      
      // Extract enhanced error details if available
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      const errorDetails = {
        category: (error as any)?.category,
        userGuidance: (error as any)?.userGuidance,
        technicalDetails: (error as any)?.technicalDetails,
        retryable: (error as any)?.retryable !== undefined ? (error as any).retryable : true
      };
      
      // Format user-friendly error message if available
      const displayMessage = (error as any)?.userGuidance 
        ? formatErrorForUser({ 
            message: errorMessage, 
            category: errorDetails.category,
            userGuidance: errorDetails.userGuidance,
            retryable: errorDetails.retryable
          })
        : errorMessage;
      
      dispatch(setError(displayMessage));
      dispatch(setLoading({ 
        isLoading: false,
        stage: 'error',
        message: displayMessage
      }));
      dispatch(setBackgroundUpload({
        isUploading: false,
        error: displayMessage,
        errorDetails
      }));
      
      setCanContinue(false);
    }
  }, [dispatch, effectiveReportId, maxFileSize, backgroundUpload, allowContinueWhileUploading]);

  // Handle retry for failed uploads
  const handleRetry = useCallback(async () => {
    if (uploadErrors.length === 0 || !filesSelected.length) {
      return;
    }
    
    setRetrying(true);
    
    // Filter out files that had errors and are retryable
    const retryableErrorFiles = uploadErrors
      .filter(error => error.retryable)
      .map(error => filesSelected.find(file => file.name === error.file))
      .filter(Boolean) as File[];
    
    if (retryableErrorFiles.length > 0) {
      // Clear errors related to these files
      setUploadErrors(prev => prev.filter(err => 
        !retryableErrorFiles.some(file => file.name === err.file)
      ));
      
      // Retry upload
      await handleUpload(retryableErrorFiles);
    }
    
    setRetrying(false);
  }, [uploadErrors, filesSelected, handleUpload]);

  // Handle continue action (proceed to next step while uploads continue in background)
  const handleContinue = () => {
    dispatch(setActiveStep(1)); // Move to next step
  };

  // Set up react-dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleUpload,
    accept: acceptedFileTypes,
    maxFiles,
    disabled: loading.isLoading || retrying
  });

  return (
    <Box sx={{ mt: 3 }}>
      <Typography variant="h6" gutterBottom>
        Carica i documenti del sinistro
      </Typography>
      
      <Typography variant="body2" color="text.secondary" paragraph>
        Trascina e rilascia i file o clicca per selezionarli. Puoi caricare fino a {maxFiles} file.
      </Typography>
      
      {/* Dropzone for file upload */}
      <Paper
        {...getRootProps()}
        elevation={isDragActive ? 3 : 1}
        sx={{
          p: 4,
          borderRadius: 2,
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'divider',
          bgcolor: isDragActive ? 'action.hover' : 'background.paper',
          textAlign: 'center',
          cursor: loading.isLoading || retrying ? 'not-allowed' : 'pointer',
          transition: 'all 0.3s ease',
          '&:hover': {
            bgcolor: 'action.hover',
            borderColor: 'primary.light'
          }
        }}
      >
        <input {...getInputProps()} />
        
        {loading.isLoading || retrying ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <CircularProgress size={40} sx={{ mb: 2 }} />
            <Typography>Attendere durante il caricamento...</Typography>
          </Box>
        ) : isDragActive ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <CloudUploadIcon color="primary" sx={{ fontSize: 48, mb: 2 }} />
            <Typography>Rilascia i file qui</Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <UploadFileIcon sx={{ fontSize: 48, mb: 2, color: 'text.secondary' }} />
            <Typography>Trascina i file qui o clicca per selezionarli</Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              Formati supportati: PDF, DOCX, DOC, TXT
            </Typography>
          </Box>
        )}
      </Paper>
      
      {/* Background upload progress tracker */}
      <UploadProgressTracker onRetry={handleRetry} />
      
      {/* Continue button - visible when continuing is allowed and files are being uploaded */}
      {allowContinueWhileUploading && backgroundUpload?.isUploading && canContinue && (
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button 
            variant="contained" 
            color="primary"
            onClick={handleContinue}
            endIcon={<CloudUploadIcon />}
          >
            Continua mentre i file si caricano
          </Button>
        </Box>
      )}
      
      {/* Completion message */}
      {!backgroundUpload?.isUploading && !backgroundUpload?.error && backgroundUpload?.uploadedFiles > 0 && (
        <Box sx={{ mt: 3, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <CloudDoneIcon color="success" sx={{ mr: 1 }} />
          <Typography color="success.main">
            {backgroundUpload.uploadedFiles} file caricati con successo
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default FileUploader; 