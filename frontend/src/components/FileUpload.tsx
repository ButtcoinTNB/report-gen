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
import BackupIcon from '@mui/icons-material/Backup';
import { uploadApi } from '../services'; // Updated import path
import { useDropzone } from 'react-dropzone';
import { UploadService, CHUNKED_UPLOAD_SIZE_THRESHOLD } from '../services/api/UploadService';
import { adaptApiResponse } from '../utils/adapters';
import { logger } from '../utils/logger';

interface Props {
  onUploadSuccess: (reportId: string) => void;  // UUID
  onError: (error: Error) => void;
}

// CamelCase interface for frontend use
interface UploadResponseCamel {
  reportId: string;  
  files: Array<{
    fileId: string;  
    filename: string;
    filePath: string;
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
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [totalSize, setTotalSize] = useState<number>(0);
  const [sizeWarning, setSizeWarning] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [progressMessage, setProgressMessage] = useState<string>('');
  
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
      setUploadError("La dimensione totale dei file supera il limite di 100MB. Rimuovi alcuni file prima di caricare.");
    } else {
      setSizeWarning(null);
      if (uploadError === "La dimensione totale dei file supera il limite di 100MB. Rimuovi alcuni file prima di caricare.") {
        setUploadError(null);
      }
    }
  }, [files, uploadError]);

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
  
  // Determine if a file is large and should use chunked upload
  const isLargeFile = (file: File) => {
    return file.size > CHUNKED_UPLOAD_SIZE_THRESHOLD;
  };
  
  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Simply update the files state and show filename
    setFiles((prev) => [...prev, ...acceptedFiles]);
    setUploadError(null);
  }, []);
  
  const handleSubmit = async () => {
    if (files.length === 0) return;
    
    try {
      setUploading(true);
      setProgress(0);
      setProgressMessage('Preparing files...');
      
      // Initialize the upload service
      const uploadService = new UploadService();
      
      // Use the uploadFiles method which now handles both regular and chunked uploads
      const response = await uploadService.uploadFiles(files, (progressValue: number) => {
        setProgress(progressValue);
        
        // Update message based on progress
        if (progressValue < 25) {
          setProgressMessage(`Starting upload... ${progressValue}%`);
        } else if (progressValue < 50) {
          setProgressMessage(`Uploading files... ${progressValue}%`);
        } else if (progressValue < 75) {
          setProgressMessage(`Processing... ${progressValue}%`);
        } else if (progressValue < 100) {
          setProgressMessage(`Almost done... ${progressValue}%`);
        } else {
          setProgressMessage('Upload complete!');
        }
      });
      
      // Wait a moment to show 100% progress
      setTimeout(() => {
        // Call the onUploadSuccess callback with the report ID
        if (response && response.reportId) {
          onUploadSuccess(response.reportId);
        } else {
          throw new Error('No report ID received from server');
        }
      }, 1000);
      
    } catch (error) {
      logger.error('Error uploading files:', error);
      setUploadError(error instanceof Error ? error.message : 'Unknown error during upload');
      onError(error instanceof Error ? error : new Error('Unknown error during upload'));
    } finally {
      setUploading(false);
    }
  };
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: uploading
  });

  const handleRemoveFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
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
                    <IconButton 
                      edge="end" 
                      aria-label="delete" 
                      onClick={() => handleRemoveFile(index)}
                      disabled={uploading}
                    >
                      <DeleteIcon />
                    </IconButton>
                  }
                >
                  <ListItemIcon>{getFileIcon(file)}</ListItemIcon>
                  <ListItemText 
                    primary={file.name} 
                    secondary={
                      <React.Fragment>
                        <Typography variant="body2" component="span">
                          {getFileSize(file.size)}
                        </Typography>
                        {isLargeFile(file) && (
                          <Chip 
                            size="small" 
                            label="Chunked Upload" 
                            color="primary" 
                            icon={<BackupIcon />} 
                            sx={{ ml: 1, height: 20, '& .MuiChip-label': { fontSize: '0.7rem', px: 1 } }}
                          />
                        )}
                      </React.Fragment>
                    }
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
        
        {uploadError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {uploadError}
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