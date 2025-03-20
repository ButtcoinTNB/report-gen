import React, { useState, useCallback, useEffect } from 'react';
import { Box, Typography, Paper, Button, Chip, Stack, Alert } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DescriptionIcon from '@mui/icons-material/Description';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import ImageIcon from '@mui/icons-material/Image';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import DeleteIcon from '@mui/icons-material/Delete';
import { useDropzone } from 'react-dropzone';
import { uploadApi } from '../services';
import LoadingIndicator, { LoadingState, LoadingStage } from './LoadingIndicator';

// Maximum total size (1GB)
const MAX_TOTAL_SIZE = 1024 * 1024 * 1024;
// Threshold for chunked upload (files larger than 50MB will use chunked upload)
const CHUNKED_UPLOAD_THRESHOLD = 50 * 1024 * 1024;

export interface DocumentUploadProps {
  onUploadComplete: (reportId: string) => void;
  maxFiles?: number;
  acceptedFileTypes?: string[];
  reportId?: string;
}

interface FileWithPreview extends File {
  preview?: string;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadComplete,
  maxFiles = 10,
  acceptedFileTypes = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png'],
  reportId
}) => {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [rejectedFiles, setRejectedFiles] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>({
    isLoading: false,
    progress: 0,
    stage: 'initial',
    message: '',
    error: null,
    attempt: 1,
    maxAttempts: 3
  });

  const getFileIcon = (fileType: string) => {
    if (fileType.includes('pdf')) return <PictureAsPdfIcon />;
    if (fileType.includes('doc')) return <DescriptionIcon />;
    if (fileType.includes('image') || /\.(jpg|jpeg|png|gif)$/i.test(fileType)) return <ImageIcon />;
    return <InsertDriveFileIcon />;
  };

  const onDrop = useCallback(async (acceptedFiles: File[], fileRejections: any[]) => {
    // Check that we haven't exceeded the max number of files
    if (files.length + acceptedFiles.length > maxFiles) {
      setError(`Non puoi caricare più di ${maxFiles} file.`);
      return;
    }

    // Check total size
    const totalSize = [...files, ...acceptedFiles].reduce((sum, file) => sum + file.size, 0);
    if (totalSize > MAX_TOTAL_SIZE) {
      setError(`La dimensione totale dei file non può superare 1GB.`);
      return;
    }

    // No errors, so proceed with setting files
    setError(null);
    setFiles(prev => [
      ...prev,
      ...acceptedFiles.map(file => 
        Object.assign(file, {
          preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
        })
      )
    ]);
    
    setRejectedFiles(fileRejections);
  }, [files, maxFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
    maxFiles,
  });

  const uploadFiles = async () => {
    if (files.length === 0) return;
    
    setLoadingState({
      isLoading: true,
      progress: 0,
      stage: 'loading',
      message: 'Caricamento dei documenti in corso...',
      error: null,
      attempt: 1,
      maxAttempts: 3
    });

    try {
      // Use the adapter which provides the same interface but uses our new service layer
      const response = await uploadApi.uploadFile(files, {
        onProgress: (progress) => {
          // Update progress
          const stage: LoadingStage = progress < 100 ? 'loading' : 'analyzing';
          
          setLoadingState(prev => ({
            ...prev,
            progress: progress || 0,
            message: progress < 100 
              ? 'Caricamento dei documenti in corso...' 
              : 'Analisi dei documenti in corso...',
            stage
          }));
        }
      });

      if (response && response.report_id) {
        setLoadingState({
          isLoading: false,
          progress: 100,
          stage: 'completed',
          message: 'Caricamento completato con successo!',
          error: null,
          attempt: 1,
          maxAttempts: 3
        });
        onUploadComplete(response.report_id);
      } else {
        throw new Error('Risposta non valida dal server');
      }
    } catch (err: any) {
      console.error('Error uploading files:', err);
      setLoadingState({
        isLoading: false,
        progress: 0,
        stage: 'error',
        message: '',
        error: err.message || 'Si è verificato un errore durante il caricamento dei file.',
        attempt: 1,
        maxAttempts: 3
      });
    }
  };

  const handleRetry = () => {
    uploadFiles();
  };

  useEffect(() => {
    // Cleanup previews when component unmounts
    return () => files.forEach(file => {
      if (file.preview) URL.revokeObjectURL(file.preview);
    });
  }, [files]);

  const removeFile = (index: number) => {
    setFiles(prev => {
      const newFiles = [...prev];
      if (newFiles[index].preview) {
        URL.revokeObjectURL(newFiles[index].preview!);
      }
      newFiles.splice(index, 1);
      return newFiles;
    });
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Paper
        {...getRootProps()}
        sx={{
          p: 3,
          border: '2px dashed #ccc',
          borderColor: isDragActive ? 'primary.main' : '#ccc',
          borderRadius: 2,
          backgroundColor: isDragActive ? 'rgba(25, 118, 210, 0.05)' : 'background.paper',
          cursor: 'pointer',
          transition: 'border-color 0.2s, background-color 0.2s',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 200,
        }}
      >
        <input {...getInputProps()} />
        <CloudUploadIcon sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive
            ? "Rilascia i file qui..."
            : "Trascina qui i file o clicca per selezionarli"}
        </Typography>
        <Typography variant="body2" color="textSecondary" textAlign="center">
          Formati supportati: PDF, DOC, DOCX, TXT, JPG, PNG (max {maxFiles} files, 1GB totale)
        </Typography>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      {rejectedFiles.length > 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          File rifiutati: {rejectedFiles.map(f => f.file.name).join(', ')}
          <br />
          Motivo: {rejectedFiles.map(f => f.errors.map((e: any) => e.message)).join(', ')}
        </Alert>
      )}

      {files.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            File selezionati ({files.length})
          </Typography>
          <Stack spacing={1} sx={{ maxHeight: '300px', overflowY: 'auto', p: 1 }}>
            {files.map((file, index) => (
              <Paper
                key={index}
                sx={{
                  p: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {getFileIcon(file.type || file.name)}
                  <Box sx={{ ml: 1 }}>
                    <Typography variant="body1" noWrap sx={{ maxWidth: '350px' }}>
                      {file.name}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                      {file.size > CHUNKED_UPLOAD_THRESHOLD && (
                        <Chip 
                          size="small" 
                          label="Caricamento a blocchi" 
                          color="info" 
                          sx={{ ml: 1, fontSize: '0.7rem' }} 
                        />
                      )}
                    </Typography>
                  </Box>
                </Box>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<DeleteIcon />}
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(index);
                  }}
                >
                  Rimuovi
                </Button>
              </Paper>
            ))}
          </Stack>

          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              color="primary"
              size="large"
              disabled={files.length === 0 || loadingState.isLoading}
              onClick={uploadFiles}
            >
              Carica {files.length} file
            </Button>
          </Box>
        </Box>
      )}

      <LoadingIndicator 
        loadingState={loadingState}
        onRetry={handleRetry}
        variant="linear"
      />
    </Box>
  );
};

export default DocumentUpload; 