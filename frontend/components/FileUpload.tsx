import React, { useState, useCallback, useEffect } from 'react';
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
  Chip,
  LinearProgress,
  Card,
  CardContent,
  Divider
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import DeleteIcon from '@mui/icons-material/Delete';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import ImageIcon from '@mui/icons-material/Image';
import DescriptionIcon from '@mui/icons-material/Description';
import { uploadFile } from '../api/upload';
import { useDropzone } from 'react-dropzone';

interface Props {
  onUploadSuccess: (reportId: string) => void;  // UUID
  onError: (error: Error) => void;
}

interface UploadResponse {
  report_id: string;  // UUID
  files: Array<{
    file_id: string;  // UUID
    filename: string;
    file_path: string;
  }>;
  message: string;
}

interface ProgressUpdate {
  step?: number;
  message?: string;
  progress: number;
}

const FileUpload: React.FC<Props> = ({ onUploadSuccess, onError }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalSize, setTotalSize] = useState<number>(0);
  const [sizeWarning, setSizeWarning] = useState<string | null>(null);
  // Using a default template ID of 1, no dropdown needed
  const templateId = 1;
  
  // Maximum allowed size in bytes (100MB)
  const MAX_TOTAL_SIZE = 100 * 1024 * 1024;
  const WARNING_THRESHOLD = 0.8 * MAX_TOTAL_SIZE; // 80% of max

  // Update total size whenever files change
  useEffect(() => {
    const newTotalSize = files.reduce((sum, file) => sum + file.size, 0);
    setTotalSize(newTotalSize);
    
    // Set warning if approaching limit
    if (newTotalSize > WARNING_THRESHOLD && newTotalSize <= MAX_TOTAL_SIZE) {
      setSizeWarning(`La dimensione totale (${getFileSize(newTotalSize)}) si sta avvicinando al limite di 100MB`);
    } else if (newTotalSize > MAX_TOTAL_SIZE) {
      setSizeWarning(`La dimensione totale (${getFileSize(newTotalSize)}) supera il limite di 100MB. Rimuovi alcuni file.`);
      setError("La dimensione totale dei file supera il limite di 100MB. Rimuovi alcuni file prima di caricare.");
    } else {
      setSizeWarning(null);
      if (error === "La dimensione totale dei file supera il limite di 100MB. Rimuovi alcuni file prima di caricare.") {
        setError(null);
      }
    }
  }, [files]);

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
  
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setUploading(true);
    setError(null);

    try {
      const response = await uploadFile(acceptedFiles);
      const data = response as UploadResponse;

      if (data.report_id) {
        onUploadSuccess(data.report_id);
      } else {
        throw new Error('No report ID received from server');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload files';
      setError(errorMessage);
      onError(new Error(errorMessage));
    } finally {
      setUploading(false);
    }
  }, [onUploadSuccess, onError]);
  
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
    maxSize: 1024 * 1024 * 1024 // 1GB
  });

  const handleRemoveFile = (index: number) => {
    setFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
  };

  // Calculate size usage percentage
  const sizePercentage = Math.min((totalSize / MAX_TOTAL_SIZE) * 100, 100);

  return (
    <Paper sx={{ 
      p: 4, 
      mb: 4,
      borderRadius: 3,
      background: 'linear-gradient(145deg, rgba(255,255,255,1) 0%, rgba(249,249,252,1) 100%)'
    }}>
      <Box component="form" noValidate>
        <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
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
            backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            '&:hover': {
              borderColor: 'primary.main',
              backgroundColor: 'action.hover'
            }
          }}
        >
          <input {...getInputProps()} />
          <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            {isDragActive ? 'Drop the files here' : 'Drag and drop files here'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            or click to select files
          </Typography>
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>
            Supported formats: PDF, DOC, DOCX, TXT, JPG, PNG
          </Typography>
          <Typography variant="caption" display="block" color="text.secondary">
            Maximum file size: 1GB
          </Typography>
        </Box>
        
        {files.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="h6">
                File Selezionati ({files.length})
              </Typography>
              <Typography variant="body2" color={sizePercentage > 80 ? "error.main" : "text.secondary"}>
                Dimensione Totale: {getFileSize(totalSize)} / 100 MB
              </Typography>
            </Box>
            
            {/* Size progress bar */}
            <Box sx={{ mb: 2 }}>
              <LinearProgress 
                variant="determinate" 
                value={sizePercentage} 
                color={sizePercentage > 80 ? "error" : "primary"}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
            
            {sizeWarning && (
              <Alert severity={sizePercentage > 100 ? "error" : "warning"} sx={{ mb: 2, borderRadius: 2 }}>
                {sizeWarning.includes("approaching") ? 
                  `La dimensione totale (${getFileSize(totalSize)}) si sta avvicinando al limite di 100MB` : 
                  `La dimensione totale (${getFileSize(totalSize)}) supera il limite di 100MB. Rimuovi alcuni file.`}
              </Alert>
            )}
            
            <List sx={{ bgcolor: 'background.paper', borderRadius: 2, mb: 2 }}>
              {files.map((file, index) => (
                <ListItem
                  key={index}
                  secondaryAction={
                    <IconButton edge="end" aria-label="delete" onClick={() => handleRemoveFile(index)}>
                      <DeleteIcon />
                    </IconButton>
                  }
                >
                  <ListItemIcon>{getFileIcon(file)}</ListItemIcon>
                  <ListItemText 
                    primary={file.name} 
                    secondary={`${getFileSize(file.size)} • ${file.type || 'Unknown type'}`}
                    primaryTypographyProps={{ 
                      noWrap: true, 
                      style: { maxWidth: '60vw' } 
                    }}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        )}
        
        {uploading && (
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <CircularProgress size={24} />
            <Typography variant="body2" sx={{ mt: 1 }}>
              Uploading files...
            </Typography>
          </Box>
        )}
        
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
        
        <Button
          type="submit"
          variant="contained"
          color="primary"
          size="large"
          fullWidth
          disabled={uploading || files.length === 0 || totalSize > MAX_TOTAL_SIZE}
          sx={{ 
            py: 1.5,
            position: 'relative',
            fontWeight: 500
          }}
        >
          {uploading ? (
            <>
              <CircularProgress 
                size={24} 
                color="inherit" 
                sx={{ 
                  position: 'absolute',
                  left: 'calc(50% - 12px)'
                }} 
              />
              <span style={{ opacity: 0 }}>Elaborazione...</span>
            </>
          ) : files.length > 0 ? 'Carica Documenti' : 'Seleziona File da Caricare'}
        </Button>
      </Box>
    </Paper>
  );
};

export default FileUpload; 