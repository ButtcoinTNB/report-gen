import React, { useState, useCallback, useRef, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Button, 
  LinearProgress, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText,
  IconButton,
  Chip,
  Tooltip
} from '@mui/material';
import { 
  CloudUpload as UploadIcon, 
  InsertDriveFile as FileIcon,
  PictureAsPdf as PdfIcon,
  Description as DocIcon,
  Image as ImageIcon,
  Delete as DeleteIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import { useTask } from '../context/TaskContext';
import { useErrorHandler } from '../hooks/useErrorHandler';
import apiClient from '../services/api';

// File status types
type FileStatus = 'pending' | 'uploading' | 'success' | 'error';

// File item interface
interface FileItem {
  file: File;
  status: FileStatus;
  progress: number;
  id: string;
  error?: string;
}

// Props for the component
interface FileUploaderProps {
  accept?: string;
  maxFiles?: number;
  maxSize?: number; // in bytes
  onUploadComplete?: (fileIds: string[]) => void;
}

// Helper to get file icon based on type
const getFileIcon = (file: File): React.ReactElement => {
  const type = file.type.toLowerCase();
  
  if (type.includes('pdf')) {
    return <PdfIcon color="primary" />;
  } else if (type.includes('word') || type.includes('document')) {
    return <DocIcon color="primary" />;
  } else if (type.includes('image')) {
    return <ImageIcon color="primary" />;
  } else {
    return <FileIcon color="primary" />;
  }
};

// Format file size
const formatSize = (bytes: number): string => {
  if (bytes < 1024) {
    return `${bytes} B`;
  } else if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  } else {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
};

const FileUploader: React.FC<FileUploaderProps> = ({
  accept = '.pdf,.doc,.docx,.jpg,.jpeg,.png',
  maxFiles = 5,
  maxSize = 10 * 1024 * 1024, // 10MB
  onUploadComplete
}) => {
  const { task, updateProgress, updateMetrics, updateStage } = useTask();
  const { handleError, wrapPromise } = useErrorHandler();
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Check if files can be added
  const canAddFiles = files.length < maxFiles;
  
  // Calculate overall progress
  const totalProgress = files.length > 0
    ? files.reduce((sum, file) => sum + file.progress, 0) / files.length
    : 0;
  
  // Handle file browser open
  const handleOpenFileBrowser = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };
  
  // Handle file addition from file input
  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      handleFilesAdded(Array.from(event.target.files));
    }
    
    // Reset the input value so the same file can be selected again
    if (event.target) {
      event.target.value = '';
    }
  };
  
  // Handle drag events
  const handleDragEnter = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);
  
  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);
  
  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);
  
  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFilesAdded(droppedFiles);
  }, []);
  
  // Process and validate added files
  const handleFilesAdded = (newFiles: File[]) => {
    if (!canAddFiles) {
      handleError(new Error(`Puoi caricare al massimo ${maxFiles} file.`));
      return;
    }
    
    const availableSlots = maxFiles - files.length;
    const filesToAdd = newFiles.slice(0, availableSlots);
    
    // Validate files
    const validatedFiles = filesToAdd.map((file) => {
      // Check file size
      if (file.size > maxSize) {
        return {
          file,
          status: 'error' as const,
          progress: 0,
          id: Math.random().toString(36).substring(7),
          error: `Il file supera la dimensione massima di ${formatSize(maxSize)}.`
        };
      }
      
      // Check file type (based on extension and MIME type)
      const fileExtension = file.name.split('.').pop()?.toLowerCase() || '';
      const acceptedTypes = accept.split(',').map(type => type.trim().toLowerCase());
      
      const isAcceptedExtension = acceptedTypes.some(type => {
        if (type.startsWith('.')) {
          return `.${fileExtension}` === type;
        }
        return false;
      });
      
      const isAcceptedMimeType = acceptedTypes.some(type => {
        if (!type.startsWith('.')) {
          return file.type.includes(type.replace('*', ''));
        }
        return false;
      });
      
      if (!isAcceptedExtension && !isAcceptedMimeType) {
        return {
          file,
          status: 'error' as const,
          progress: 0,
          id: Math.random().toString(36).substring(7),
          error: `Tipo di file non supportato. Formati accettati: ${accept}`
        };
      }
      
      // Valid file
      return {
        file,
        status: 'pending' as const,
        progress: 0,
        id: Math.random().toString(36).substring(7)
      };
    });
    
    // Add to files state
    setFiles(prevFiles => [...prevFiles, ...validatedFiles]);
    
    // Update task metrics
    updateMetrics({
      uploadedFiles: 0,
      totalFiles: validatedFiles.filter(f => f.status !== 'error').length
    });
  };
  
  // Remove a file from the list
  const handleRemoveFile = (id: string) => {
    setFiles(prevFiles => {
      const newFiles = prevFiles.filter(file => file.id !== id);
      
      // Update task metrics
      updateMetrics({
        uploadedFiles: newFiles.filter(f => f.status === 'success').length,
        totalFiles: newFiles.filter(f => f.status !== 'error').length
      });
      
      return newFiles;
    });
  };
  
  // Upload a specific file
  const uploadFile = async (fileItem: FileItem) => {
    // Skip files that are already uploading, completed, or have errors
    if (fileItem.status !== 'pending') {
      return;
    }
    
    // Update file status to uploading
    setFiles(prevFiles => 
      prevFiles.map(f => 
        f.id === fileItem.id ? { ...f, status: 'uploading' as const } : f
      )
    );
    
    try {
      // Make the upload request
      await wrapPromise(
        apiClient.uploadFile(
          '/api/uploads',
          fileItem.file,
          { documentType: 'insurance' },
          (progress) => {
            // Update file progress
            setFiles(prevFiles => 
              prevFiles.map(f => 
                f.id === fileItem.id ? { ...f, progress } : f
              )
            );
            
            // Update overall task progress
            const allFiles = [...files.map(f => 
              f.id === fileItem.id ? { ...f, progress } : f
            )];
            
            const totalProgress = allFiles.reduce((sum, file) => sum + file.progress, 0) / allFiles.length;
            updateProgress(totalProgress, `Caricamento in corso (${Math.round(totalProgress)}%)`);
          }
        )
      );
      
      // Update file status to success
      setFiles(prevFiles => {
        const newFiles = prevFiles.map(f => 
          f.id === fileItem.id ? { ...f, status: 'success' as const, progress: 100 } : f
        );
        
        // Update task metrics
        const successCount = newFiles.filter(f => f.status === 'success').length;
        const totalCount = newFiles.filter(f => f.status !== 'error').length;
        
        updateMetrics({
          uploadedFiles: successCount,
          totalFiles: totalCount
        });
        
        // If all files are processed, call the completion handler
        if (successCount === totalCount && successCount > 0) {
          const fileIds = newFiles
            .filter(f => f.status === 'success')
            .map(f => f.id);
            
          onUploadComplete?.(fileIds);
        }
        
        return newFiles;
      });
    } catch (error) {
      // Update file status to error
      setFiles(prevFiles => 
        prevFiles.map(f => 
          f.id === fileItem.id ? { 
            ...f, 
            status: 'error' as const, 
            error: error instanceof Error ? error.message : 'Errore durante il caricamento'
          } : f
        )
      );
    }
  };
  
  // Upload all pending files
  const uploadAllFiles = () => {
    const pendingFiles = files.filter(f => f.status === 'pending');
    
    if (pendingFiles.length === 0) {
      return;
    }
    
    // Start uploading each file
    pendingFiles.forEach(fileItem => {
      uploadFile(fileItem);
    });
  };
  
  // Handle all uploads complete
  const checkAllUploadsComplete = useCallback(() => {
    const allCompleted = files.length > 0 && 
      files.every(f => f.status === 'success' || f.status === 'error');
    
    const successfulFiles = files.filter(f => f.status === 'success');
    
    if (allCompleted && successfulFiles.length > 0) {
      const fileIds = successfulFiles.map(f => f.id);
      
      // Update task progress and message
      updateMetrics({
        progress: 100,
        message: 'Caricamento completato. Avvio estrazione del contenuto...',
        fileIds: fileIds // Add fileIds to the task state
      });
      
      // Transition to next stage after short delay for user to see completion
      setTimeout(() => {
        // Only transition if we're still in upload stage (user hasn't navigated away)
        if (task.stage === 'upload') {
          // Use updateStage instead of transitionToStage
          updateStage('extraction', 'Estrazione del contenuto in corso');
          
          // Call onUploadComplete callback if provided
          onUploadComplete?.(fileIds);
        }
      }, 1500);
    } else if (allCompleted && successfulFiles.length === 0) {
      // All files failed - show error
      handleError(new Error('Nessun file è stato caricato con successo. Riprova.'));
    }
  }, [files, handleError, onUploadComplete, task.stage, updateMetrics, updateStage]);
  
  // Check for completion whenever file statuses change
  useEffect(() => {
    checkAllUploadsComplete();
  }, [files.map(f => f.status).join(','), checkAllUploadsComplete]);
  
  // Render file item
  const renderFileItem = (fileItem: FileItem) => {
    const { file, status, progress, error } = fileItem;
    
    // Determine status icon and color
    let statusIcon = null;
    let statusColor = 'default';
    let statusLabel = '';
    
    switch (status) {
      case 'pending':
        statusLabel = 'In attesa';
        statusColor = 'default';
        break;
      case 'uploading':
        statusLabel = `${Math.round(progress)}%`;
        statusColor = 'primary';
        break;
      case 'success':
        statusIcon = <SuccessIcon fontSize="small" />;
        statusLabel = 'Completato';
        statusColor = 'success';
        break;
      case 'error':
        statusIcon = <ErrorIcon fontSize="small" />;
        statusLabel = 'Errore';
        statusColor = 'error';
        break;
    }
    
    return (
      <ListItem
        key={fileItem.id}
        secondaryAction={
          status !== 'uploading' && (
            <IconButton 
              edge="end" 
              aria-label="delete" 
              onClick={() => handleRemoveFile(fileItem.id)}
            >
              <DeleteIcon />
            </IconButton>
          )
        }
      >
        <ListItemIcon>
          {getFileIcon(file)}
        </ListItemIcon>
        <ListItemText
          primary={file.name}
          secondary={
            <>
              {formatSize(file.size)}
              {error && (
                <Typography 
                  component="span" 
                  variant="body2" 
                  color="error" 
                  sx={{ display: 'block' }}
                >
                  {error}
                </Typography>
              )}
              {status === 'uploading' && (
                <LinearProgress 
                  variant="determinate" 
                  value={progress} 
                  sx={{ mt: 1, height: 4, borderRadius: 2 }} 
                />
              )}
            </>
          }
        />
        <Chip 
          label={statusLabel}
          size="small"
          color={statusColor as any}
          icon={statusIcon}
          sx={{ ml: 1 }}
        />
      </ListItem>
    );
  };
  
  return (
    <Box sx={{ mb: 3 }}>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={accept}
        onChange={handleFileInputChange}
        style={{ display: 'none' }}
        aria-label="Input file nascosto"
      />
      
      {/* Drag and drop area */}
      <Paper
        variant="outlined"
        sx={{
          p: 3,
          mb: 2,
          borderRadius: 2,
          borderStyle: 'dashed',
          borderWidth: 2,
          borderColor: isDragging ? 'primary.main' : 'divider',
          bgcolor: isDragging ? 'action.hover' : 'background.paper',
          transition: 'all 0.2s ease'
        }}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <Box 
          sx={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center',
            py: 2
          }}
        >
          <UploadIcon color="primary" sx={{ fontSize: 48, mb: 2 }} />
          
          <Typography variant="h6" align="center" gutterBottom>
            {isDragging ? 'Rilascia qui i file' : 'Trascina qui i file'}
          </Typography>
          
          <Typography variant="body2" align="center" color="text.secondary" paragraph>
            oppure
          </Typography>
          
          <Button
            variant="contained"
            component="span"
            onClick={handleOpenFileBrowser}
            disabled={!canAddFiles}
          >
            Seleziona file
          </Button>
          
          <Typography variant="caption" align="center" color="text.secondary" sx={{ mt: 2 }}>
            Formati supportati: PDF, DOCX, JPG, PNG
            <br />
            Dimensione massima: {formatSize(maxSize)} per file, massimo {maxFiles} file
          </Typography>
        </Box>
      </Paper>
      
      {/* File list */}
      {files.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="subtitle2">
              File ({files.length}/{maxFiles})
            </Typography>
            
            <Button
              variant="outlined"
              size="small"
              onClick={uploadAllFiles}
              disabled={!files.some(f => f.status === 'pending')}
            >
              Carica tutti
            </Button>
          </Box>
          
          <Paper variant="outlined" sx={{ borderRadius: 2 }}>
            <List sx={{ p: 0 }}>
              {files.map(fileItem => renderFileItem(fileItem))}
            </List>
          </Paper>
          
          {/* Overall progress */}
          {files.some(f => f.status === 'uploading') && (
            <Box sx={{ mt: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2" color="text.secondary">
                  Progresso totale
                </Typography>
                <Typography variant="body2">
                  {Math.round(totalProgress)}%
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={totalProgress} 
                sx={{ height: 6, borderRadius: 3 }} 
              />
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
};

export default FileUploader; 