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

interface FileUploadProps {
  onUploadSuccess: (reportId: number) => void;
}

interface UploadResponse {
  report_id: number;
  [key: string]: any;
}

interface ProgressUpdate {
  step?: number;
  message?: string;
  progress: number;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
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
      setError("Seleziona almeno un file da caricare.");
      return;
    }
    
    // Double-check size before submitting
    if (totalSize > MAX_TOTAL_SIZE) {
      setError("La dimensione totale dei file supera il limite di 100MB. Rimuovi alcuni file prima di caricare.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Pass the files array directly to the uploadFile function
      const response = await uploadFile(files, templateId) as UploadResponse;
      console.log("Upload response:", response);
      
      // Check for success
      if (response && response.report_id) {
        console.log("Upload success with report ID:", response.report_id);
        
        // Call onUploadSuccess directly to proceed to the next step
        onUploadSuccess(response.report_id);
      } else {
        setError("Nessun ID report ricevuto dal server.");
      }
    } catch (err) {
      console.error("Error uploading files:", err);
      setError(err instanceof Error ? err.message : "Impossibile caricare i file. Riprova.");
    } finally {
      setLoading(false);
    }
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
      <Box component="form" onSubmit={handleSubmit} noValidate>
        <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
          Carica Documenti
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
            {isDragActive ? 'Rilascia i file qui' : 'Trascina e rilascia i file qui'}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            o clicca per sfogliare i file
          </Typography>
          <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 1 }}>
            Supporta file PDF, DOC, DOCX, TXT e immagini
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
        
        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {error.includes("select at least one file") ? 
              "Seleziona almeno un file da caricare." : 
              error.includes("Total file size exceeds") ? 
              "La dimensione totale dei file supera il limite di 100MB. Rimuovi alcuni file prima di caricare." : 
              error}
          </Alert>
        )}
        
        <Button
          type="submit"
          variant="contained"
          color="primary"
          size="large"
          fullWidth
          disabled={loading || files.length === 0 || totalSize > MAX_TOTAL_SIZE}
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
              <span style={{ opacity: 0 }}>Elaborazione...</span>
            </>
          ) : files.length > 0 ? 'Carica Documenti' : 'Seleziona File da Caricare'}
        </Button>
      </Box>
    </Paper>
  );
};

export default FileUpload; 