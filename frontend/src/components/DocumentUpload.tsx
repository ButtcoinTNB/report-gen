import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Alert,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Description as DescriptionIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { uploadFile } from '../../api/upload';
import LoadingIndicator, { LoadingState } from './LoadingIndicator';

// Define the response type from the uploadFile function
interface UploadResponse {
  report_id?: string;
  message?: string;
  file_count?: number;
  status?: string;
  detail?: string;
}

interface DocumentUploadProps {
  onUploadComplete: (reportId: string) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ onUploadComplete }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [loadingState, setLoadingState] = useState<LoadingState>({
    isLoading: false,
    progress: 0,
    stage: 'initial'
  });
  const [error, setError] = useState<string | null>(null);
  const [totalSize, setTotalSize] = useState<number>(0);
  const MAX_TOTAL_SIZE = 1073741824; // 1GB

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files (due to file type or size constraints)
    if (rejectedFiles.length > 0) {
      const errors = rejectedFiles.map(file => {
        const error = file.errors[0];
        if (error.code === 'file-too-large') {
          return `"${file.file.name}" è troppo grande (max 1GB per file)`;
        }
        if (error.code === 'file-invalid-type') {
          return `"${file.file.name}" non è un formato supportato (solo PDF, DOC, DOCX, TXT, JPG, PNG)`;
        }
        return `"${file.file.name}" è stato rifiutato: ${error.message}`;
      });
      setError(errors.join('. '));
      return;
    }
    
    // Calculate total size
    const newTotalSize = acceptedFiles.reduce((sum, file) => sum + file.size, 0);
    setTotalSize(prevSize => prevSize + newTotalSize);
    
    // Check total size before accepting files
    const updatedTotalSize = totalSize + newTotalSize;
    if (updatedTotalSize > MAX_TOTAL_SIZE) {
      setError(`Il caricamento totale supera il limite di 1GB. Attuale: ${(updatedTotalSize / (1024 * 1024 * 1024)).toFixed(2)}GB`);
      return;
    }
    
    setFiles(prevFiles => [...prevFiles, ...acceptedFiles]);
    setError(null);
  }, [totalSize]);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxSize: MAX_TOTAL_SIZE
  });

  const removeFile = (index: number) => {
    setFiles(prevFiles => {
      const fileToRemove = prevFiles[index];
      setTotalSize(prevSize => prevSize - fileToRemove.size);
      
      const newFiles = [...prevFiles];
      newFiles.splice(index, 1);
      return newFiles;
    });
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Seleziona almeno un documento da caricare.');
      return;
    }

    // Final check on total size before uploading
    const totalFileSize = files.reduce((sum, file) => sum + file.size, 0);
    if (totalFileSize > MAX_TOTAL_SIZE) {
      setError(`Il caricamento totale supera il limite di 1GB. Attuale: ${(totalFileSize / (1024 * 1024 * 1024)).toFixed(2)}GB`);
      return;
    }

    setError(null);
    setLoadingState({
      isLoading: true,
      progress: 0,
      stage: 'loading',
      message: 'Caricamento dei documenti in corso...'
    });

    try {
      // Use the uploadFile function with progress tracking
      const response = await uploadFile(files, 1, (progressEvent: {loaded: number, total?: number}) => {
        if (progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setLoadingState(prevState => ({
            ...prevState,
            progress,
            message: `Caricamento: ${progress}%`
          }));
        }
      }) as UploadResponse;

      if (response && response.report_id) {
        setLoadingState({
          isLoading: false,
          progress: 100,
          stage: 'completed',
          message: 'Caricamento completato!'
        });
        onUploadComplete(response.report_id);
      } else {
        setLoadingState({
          isLoading: false,
          stage: 'error',
          error: response.detail || 'Si è verificato un errore durante il caricamento.'
        });
      }
    } catch (err: any) {
      console.error('Upload error:', err);
      const errorMessage = err.message || 'Si è verificato un errore durante il caricamento.';
      
      setLoadingState({
        isLoading: false,
        stage: 'error',
        error: errorMessage
      });
    }
  };

  const handleRetry = () => {
    setLoadingState({
      isLoading: false,
      progress: 0,
      stage: 'initial'
    });
    setError(null);
    // Don't auto-trigger upload on retry to let the user make adjustments if needed
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Carica Documenti
        </Typography>

        <Box
          {...getRootProps()}
          sx={{
            border: '2px dashed',
            borderColor: isDragActive ? 'primary.main' : 'grey.300',
            borderRadius: 1,
            p: 3,
            textAlign: 'center',
            cursor: 'pointer',
            mb: 2,
            backgroundColor: isDragActive ? 'rgba(25, 118, 210, 0.04)' : 'transparent',
            transition: 'background-color 0.2s, border-color 0.2s',
            '&:hover': {
              backgroundColor: 'rgba(0, 0, 0, 0.04)',
            },
          }}
        >
          <input {...getInputProps()} />
          <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
          <Typography variant="body1" gutterBottom>
            {isDragActive
              ? 'Rilascia qui i file'
              : 'Trascina i file qui, o clicca per selezionarli'}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Formati supportati: PDF, DOC, DOCX, TXT, JPG, PNG (max 1GB)
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {files.length > 0 && (
          <>
            <List sx={{ bgcolor: 'background.paper', borderRadius: 1 }}>
              {files.map((file, index) => (
                <ListItem key={`${file.name}-${index}`}>
                  <ListItemIcon>
                    <DescriptionIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary={file.name}
                    secondary={`${(file.size / (1024 * 1024)).toFixed(2)} MB • ${file.type || 'Tipo sconosciuto'}`}
                  />
                  <ListItemSecondaryAction>
                    <IconButton edge="end" aria-label="delete" onClick={() => removeFile(index)}>
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
            
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
              <Typography variant="body2" color="textSecondary">
                {files.length} file selezionati ({(totalSize / (1024 * 1024)).toFixed(2)} MB)
              </Typography>
              <Button
                variant="contained"
                color="primary"
                onClick={handleUpload}
                disabled={loadingState.isLoading || files.length === 0}
              >
                Carica
              </Button>
            </Box>
          </>
        )}

        {/* Use our standardized loading indicator */}
        <LoadingIndicator
          state={loadingState}
          variant="linear"
          onRetry={handleRetry}
        />
      </CardContent>
    </Card>
  );
};

export default DocumentUpload; 