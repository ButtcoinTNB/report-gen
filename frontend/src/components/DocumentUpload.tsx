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
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Description as DescriptionIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import api from '../services/api';

interface DocumentUploadProps {
  onUploadComplete: (documentIds: string[]) => void;
  isLoading: boolean;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ onUploadComplete, isLoading }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
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

    // Check if adding these files would exceed total size limit
    const newTotalSize = files.reduce((sum, file) => sum + file.size, 0) + 
                        acceptedFiles.reduce((sum, file) => sum + file.size, 0);
    
    if (newTotalSize > MAX_TOTAL_SIZE) {
      setError(`Il caricamento totale supera il limite di 1GB. Attuale: ${(newTotalSize / (1024 * 1024 * 1024)).toFixed(2)}GB`);
      return;
    }

    setFiles((prevFiles) => [...prevFiles, ...acceptedFiles]);
    setTotalSize(newTotalSize);
    setError(null);
  }, [files]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'text/plain': ['.txt'],
    },
    maxSize: 1073741824, // 1GB
  });

  const removeFile = (index: number) => {
    const removedFile = files[index];
    setFiles((prevFiles) => prevFiles.filter((_, i) => i !== index));
    setTotalSize((prevSize) => prevSize - removedFile.size);
    
    // Clear error if it was about file size
    if (error && (error.includes('limite di 1GB') || error.includes('supera il limite'))) {
      setError(null);
    }
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
    setUploadProgress(0);

    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    try {
      // Use the correct API endpoint for document uploads
      const response = await api.post('/upload/documents', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          }
        },
      });

      if (response.data && response.data.report_id) {
        onUploadComplete([response.data.report_id]);
      } else {
        setError(response.data.detail || 'Si è verificato un errore durante il caricamento.');
      }
    } catch (err: any) {
      console.error('Upload error:', err);
      const errorMessage = err.response?.data?.detail || 'Si è verificato un errore durante il caricamento.';
      
      // Handle specific error types
      if (errorMessage.includes('size exceeds')) {
        setError('Il caricamento supera il limite di 1GB. Riduci la dimensione totale dei file.');
      } else if (errorMessage.includes('Unsupported file type')) {
        setError('Uno o più file sono in un formato non supportato. Utilizza solo PDF, DOC, DOCX, TXT, JPG o PNG.');
      } else {
        setError(errorMessage);
      }
    }
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
            mb: 3,
            textAlign: 'center',
            cursor: 'pointer',
            bgcolor: isDragActive ? 'action.hover' : 'background.paper',
            transition: 'all 0.2s ease',
            '&:hover': {
              bgcolor: 'action.hover',
            },
          }}
        >
          <input {...getInputProps()} />
          <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
          <Typography variant="h6" gutterBottom>
            {isDragActive ? 'Rilascia i file qui' : 'Trascina i file qui'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            o clicca per selezionare i file
          </Typography>
          <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 1 }}>
            Formati supportati: PDF, DOC, DOCX, TXT, JPG, PNG (max 1GB in totale)
          </Typography>
        </Box>

        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2">
            <strong>Come funziona:</strong> L'AI estrarrà informazioni <strong>solo dai documenti che carichi</strong>. 
            Il sistema utilizza riferimenti stilistici per formattare il report finale, ma tutto il contenuto 
            proverrà esclusivamente dai tuoi documenti e dalle informazioni aggiuntive che fornirai.
          </Typography>
        </Alert>

        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="body2">
            <strong>Nota sulla privacy:</strong> Tutti i documenti caricati e i dati generati sono temporanei e 
            verranno eliminati automaticamente dopo il download del report finale o dopo 24 ore di inattività.
          </Typography>
        </Alert>

        {files.length > 0 && (
          <>
            <List>
              {files.map((file, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <DescriptionIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary={file.name}
                    secondary={`${(file.size / 1024 / 1024).toFixed(2)} MB`}
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      aria-label="delete"
                      onClick={() => removeFile(index)}
                      disabled={isLoading}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
            <Typography variant="body2" color="text.secondary" align="right" sx={{ mt: 1 }}>
              Dimensione totale: {(totalSize / (1024 * 1024)).toFixed(2)} MB / 1024 MB
              {totalSize > MAX_TOTAL_SIZE * 0.8 && (
                <Typography component="span" color="error.main"> (Avvicinandosi al limite!)</Typography>
              )}
            </Typography>
          </>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            onClick={handleUpload}
            disabled={files.length === 0 || isLoading}
            startIcon={isLoading ? <CircularProgress size={20} /> : undefined}
          >
            {isLoading ? 'Caricamento...' : 'Carica e Analizza'}
          </Button>
        </Box>

        {isLoading && uploadProgress > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" align="center">
              Caricamento in corso: {uploadProgress}%
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default DocumentUpload; 