import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Box, 
  Container, 
  Typography, 
  Button, 
  Paper, 
  Divider,
  Grid,
  Card,
  CardContent,
  CardActions,
  Alert,
  Snackbar,
  CircularProgress,
  LinearProgress,
  IconButton,
  Tooltip
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import ShareIcon from '@mui/icons-material/Share';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { RootState } from '../store';
import { setLoadingAsync, setErrorAsync, setPreviewUrlAsync } from '../store/reportSlice';
import { DocumentPreview, DownloadProgressTracker, ReportSummary } from './DynamicComponents';
import { isBrowser, withWindow } from '../utils/environment';
import { DocumentService } from '../services/DocumentService';
import { LoadingState } from '../store/types';
import { useDispatch } from 'react-redux';
import { AppDispatch } from '../store';
import { ShareButton } from './ShareButton';
import { DocumentMetadata } from '../types/document';
import { useErrorHandler } from '../hooks/useErrorHandler';
import { useTask } from '../context/TaskContext';
import { apiConfig } from '../config/api.config';

interface EnhancedReportDownloaderProps {
  reportId: string;
  onDownloadComplete?: () => void;
  disableMetadata?: boolean;
}

/**
 * Enhanced Report Downloader component that combines document preview,
 * report metrics, and download functionality in a single interface
 */
const EnhancedReportDownloader: React.FC<EnhancedReportDownloaderProps> = ({ 
  reportId, 
  onDownloadComplete,
  disableMetadata = false
}) => {
  const dispatch = useAppDispatch();
  const documentService = DocumentService.getInstance();
  const { handleError, wrapPromise } = useErrorHandler();
  const { task, updateTask } = useTask();
  
  // Get state from Redux
  const { content, previewUrl, loading, error: storeError } = useAppSelector(
    (state: RootState) => state.report
  );
  
  // Local state
  const [downloadProgress, setDownloadProgress] = useState<number>(0);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>('report.docx');
  const [fileSize, setFileSize] = useState<number>(0);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [showShareSuccess, setShowShareSuccess] = useState<boolean>(false);
  const [qualityScore, setQualityScore] = useState<number>(0);
  const [editCount, setEditCount] = useState<number>(0);
  const [iterations, setIterations] = useState<number>(0);
  const [timeSaved, setTimeSaved] = useState<number>(120); // Default 2 hours
  const [downloadReady, setDownloadReady] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [documentData, setDocumentData] = useState<DocumentMetadata | null>(null);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const [generatingPreview, setGeneratingPreview] = useState<boolean>(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [retries, setRetries] = useState<number>(0);
  const [metadata, setMetadata] = useState<DocumentMetadata | null>(null);
  
  // Get document metadata when component mounts
  useEffect(() => {
    if (reportId) {
      fetchDocumentMetadata(reportId);
    }
    
    // Cleanup function to abort any in-progress requests
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [reportId]);
  
  // Fetch document metadata
  const fetchMetadata = useCallback(async () => {
    if (disableMetadata || !reportId) return;
    
    try {
      // Using wrapPromise will handle errors automatically
      const response = await wrapPromise(fetch(`/api/documents/${reportId}/metadata`));
      const data = await response.json();
      setMetadata(data);
    } catch (err) {
      // Error is already handled by wrapPromise
      console.debug('Metadata fetch failed, continuing without it');
      // Don't set error here as it's handled by useErrorHandler
    }
  }, [reportId, disableMetadata, wrapPromise]);
  
  // Generate preview of the document
  const handleGeneratePreview = useCallback(async () => {
    if (!reportId) {
      handleError(new Error('Report ID is required for preview'));
      return;
    }
    
    setGeneratingPreview(true);
    setPreviewError(null);
    
    try {
      const loadingState: LoadingState = {
        isLoading: true,
        stage: 'preview',
        message: 'Generating preview...',
        progress: 0
      };
      dispatch(setLoadingAsync(loadingState));
      
      const url = await documentService.generatePreview(reportId);
      if (url) {
        dispatch(setPreviewUrlAsync(url));
        setPreviewError(null);
      }
    } catch (err) {
      // Use handleError from useErrorHandler
      handleError(err, {
        showToUser: true,
        onError: (error) => {
          setPreviewError(error.message);
          setGeneratingPreview(false);
        }
      });
    } finally {
      setGeneratingPreview(false);
      const loadingState: LoadingState = {
        isLoading: false,
        stage: undefined,
        message: undefined,
        progress: undefined
      };
      dispatch(setLoadingAsync(loadingState));
    }
  }, [reportId, handleError, dispatch, documentService]);
  
  // Fetch document metadata from Supabase
  const fetchDocumentMetadata = useCallback(async (documentId: string) => {
    setIsLoading(true);
    setError(null);
    const loadingState: LoadingState = {
      isLoading: true,
      stage: 'metadata',
      message: 'Fetching document metadata...',
      progress: 0
    };
    dispatch(setLoadingAsync(loadingState));
    
    try {
      const data = await documentService.getMetadata(documentId);
      
      if (!data) {
        throw new Error('Document not found');
      }
      
      // Update all relevant state with the document data
      setDocumentData(data);
      setFileName(data.filename || 'report.docx');
      setFileSize(data.size || 0);
      setQualityScore(data.quality_score || 0);
      setEditCount(data.edit_count || 0);
      setIterations(data.iterations || 0);
      setTimeSaved(data.time_saved || 120);
      setTotalPages(data.pages || 1);
      setDownloadReady(true);
      
      // Auto-generate preview after metadata is loaded
      if (data.status === 'completed') {
        handleGeneratePreview();
      }
    } catch (error) {
      console.error('Error fetching document metadata:', error);
      setError(error instanceof Error ? error.message : 'Error fetching document metadata');
      dispatch(setErrorAsync(error instanceof Error ? error.message : 'Error fetching document metadata'));
    } finally {
      setIsLoading(false);
      const loadingState: LoadingState = {
        isLoading: false,
        stage: undefined,
        message: undefined,
        progress: undefined
      };
      dispatch(setLoadingAsync(loadingState));
    }
  }, [dispatch, documentService, handleGeneratePreview]);
  
  // Download the document with progress tracking
  const handleDownload = useCallback(async (format: 'docx' | 'pdf' = 'docx') => {
    if (!reportId) {
      handleError(new Error('Report ID is required for download'));
      return;
    }
    
    // Check if we're in a browser environment
    if (!isBrowser) {
      console.warn('Download attempted in non-browser environment');
      return;
    }

    // Create a unique task ID for this download
    const taskId = `download-${reportId}-${Date.now()}`;
    // Update task state to indicate download is starting
    updateTask({
      id: taskId,
      stage: 'finalization',
      status: 'in_progress',
      message: `Downloading ${format} document...`,
      progress: 0
    });
    
    setIsDownloading(true);
    setDownloadProgress(0);
    
    try {
      const downloadUrl = `/api/documents/${reportId}/download?format=${format}`;
      
      // Fetch with progress tracking
      const response = await fetch(downloadUrl);
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }
      
      const contentLength = response.headers.get('content-length');
      const totalBytes = contentLength ? parseInt(contentLength, 10) : 0;
      
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Unable to read response body');
      }
      
      let receivedBytes = 0;
      const chunks: Uint8Array[] = [];
      
      // Process the stream
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }
        
        chunks.push(value);
        receivedBytes += value.length;
        
        if (totalBytes > 0) {
          const progress = Math.round((receivedBytes / totalBytes) * 100);
          setDownloadProgress(progress);
          
          // Update task progress
          updateTask({
            progress
          });
        }
      }
      
      // Safely create and trigger download using withWindow helper
      withWindow((window) => {
        // Combine chunks into a single Uint8Array
        const chunksAll = new Uint8Array(receivedBytes);
        let position = 0;
        for (const chunk of chunks) {
          chunksAll.set(chunk, position);
          position += chunk.length;
        }
        
        const blob = new Blob([chunksAll], { 
          type: format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
        });
        
        // Create object URL and trigger download
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Report-${reportId}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, null);
      
      // Update download count
      try {
        await fetch(`/api/documents/${reportId}/track-download`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ format })
        });
        
        // Also update through the service
        documentService.updateDownloadCount(reportId).catch(console.error);
      } catch (err) {
        console.warn('Failed to track download:', err);
        // Non-fatal error, continue
      }
      
      // Mark the task as complete
      updateTask({
        status: 'completed',
        progress: 100,
        message: `${format.toUpperCase()} download completed`
      });
      
      setIsDownloading(false);
      setRetries(0);
      
      if (onDownloadComplete) {
        onDownloadComplete();
      }
      
    } catch (err) {
      handleError(err, {
        showToUser: true,
        onError: (error) => {
          setIsDownloading(false);
          // Mark the task as failed
          updateTask({
            status: 'failed',
            message: error.message,
            error: error.message
          });
          
          // Increment retry counter
          setRetries(prev => prev + 1);
        }
      });
    }
  }, [reportId, handleError, updateTask, onDownloadComplete, documentService]);
  
  // Generate and copy share link
  const handleShareLink = async () => {
    if (!reportId) return;
    
    try {
      const loadingState: LoadingState = {
        isLoading: true,
        stage: 'share',
        message: 'Generating share link...',
        progress: 0
      };
      dispatch(setLoadingAsync(loadingState));
      
      const response = await fetch('/api/share/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reportId })
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate share link');
      }
      
      const data = await response.json();
      setShareUrl(data.url);
    } catch (err) {
      console.error('Error generating share link:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate share link';
      dispatch(setErrorAsync(errorMessage));
    } finally {
      const loadingState: LoadingState = {
        isLoading: false,
        stage: undefined,
        message: undefined,
        progress: undefined
      };
      dispatch(setLoadingAsync(loadingState));
    }
  };
  
  // Copy share URL to clipboard
  const copyShareUrl = async () => {
    if (!isBrowser || !shareUrl) return;
    
    withWindow(async (window) => {
      try {
        if (navigator.clipboard) {
          await navigator.clipboard.writeText(shareUrl);
          setShowShareSuccess(true);
        } else {
          // Fallback method
          const textArea = document.createElement('textarea');
          textArea.value = shareUrl;
          document.body.appendChild(textArea);
          textArea.focus();
          textArea.select();
          document.execCommand('copy');
          document.body.removeChild(textArea);
          setShowShareSuccess(true);
        }
      } catch (err) {
        console.error('Failed to copy to clipboard:', err);
      }
    }, null);
  };
  
  // Close the share success notification
  const handleCloseShareNotification = () => {
    setShowShareSuccess(false);
  };
  
  // When a document is updated, clear the cache to ensure fresh data
  const invalidateDocumentCache = useCallback(() => {
    if (!reportId || !isBrowser) return;
    
    withWindow((window) => {
      if (window.localStorage) {
        try {
          const cacheKey = `supabase_documents_${JSON.stringify({
            select: '*',
            filter: { id: reportId },
            single: true
          })}`;
          localStorage.removeItem(cacheKey);
        } catch (e) {
          console.warn('Could not access localStorage', e);
        }
      }
    }, null);
  }, [reportId]);
  
  // When component unmounts, invalidate the document cache
  useEffect(() => {
    return () => {
      invalidateDocumentCache();
    };
  }, [invalidateDocumentCache]);
  
  // Handle download error notification closing
  const handleCloseDownloadError = () => {
    setDownloadError(null);
  };
  
  // Handle preview error notification closing
  const handleClosePreviewError = () => {
    setPreviewError(null);
  };
  
  if (!reportId) {
    return (
      <Container maxWidth="lg">
        <Alert severity="warning" sx={{ mt: 3 }}>
          Nessun report disponibile. Genera un report prima.
        </Alert>
      </Container>
    );
  }
  
  return (
    <Container maxWidth="lg">
      <Typography variant="h4" component="h1" gutterBottom sx={{ mt: 3 }}>
        Risultati Report
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {/* Report Summary Stats */}
      <ReportSummary 
        timeEstimate={timeSaved}
        editCount={editCount}
        qualityScore={qualityScore}
        iterations={iterations}
      />
      
      <Grid container spacing={3}>
        {/* Document Preview Section */}
        <Grid item xs={12} md={8}>
          <DocumentPreview 
            previewUrl={previewUrl}
            title="Anteprima Report Finale"
            isLoading={loading.isLoading && loading.stage === 'preview'}
            error={error}
            onRefresh={handleGeneratePreview}
          />
        </Grid>
        
        {/* Download Options Section */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Download Options
            </Typography>
            
            {/* DOCX Download */}
            <Card variant="outlined" sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="subtitle1" fontWeight="medium">
                  Documento Word
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Formato DOCX editabile, ideale per modifiche successive.
                </Typography>
              </CardContent>
              <CardActions>
                <Button 
                  fullWidth
                  variant="contained" 
                  color="primary"
                  startIcon={<DownloadIcon />}
                  onClick={() => handleDownload('docx')}
                  disabled={isDownloading || !downloadReady}
                >
                  {isDownloading ? (
                    <>
                      <CircularProgress size={20} sx={{ mr: 1 }} />
                      Downloading...
                    </>
                  ) : (
                    'Scarica DOCX'
                  )}
                </Button>
              </CardActions>
            </Card>
            
            {/* PDF Download */}
            <Card variant="outlined" sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="subtitle1" fontWeight="medium">
                  Documento PDF
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Formato professionale ideale per condivisione e stampa.
                </Typography>
              </CardContent>
              <CardActions>
                <Button 
                  fullWidth
                  variant="outlined" 
                  color="primary"
                  startIcon={<DownloadIcon />}
                  onClick={() => handleDownload('pdf')}
                  disabled={isDownloading || !downloadReady}
                >
                  {isDownloading ? (
                    <>
                      <CircularProgress size={20} sx={{ mr: 1 }} />
                      Downloading...
                    </>
                  ) : (
                    'Scarica PDF'
                  )}
                </Button>
              </CardActions>
            </Card>
            
            {/* Share Options */}
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="subtitle1" gutterBottom>
              Opzioni di Condivisione
            </Typography>
            
            <Button
              fullWidth
              variant="outlined"
              color="secondary"
              startIcon={<ShareIcon />}
              onClick={handleShareLink}
              disabled={isDownloading || loading.isLoading}
              sx={{ mb: 2 }}
            >
              Genera Link di Condivisione
            </Button>
            
            {shareUrl && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Link di condivisione:
                </Typography>
                <Box sx={{ 
                  display: 'flex', 
                  alignItems: 'center',
                  bgcolor: 'grey.100',
                  p: 1,
                  borderRadius: 1
                }}>
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {shareUrl}
                  </Typography>
                  <Tooltip title="Copia link">
                    <IconButton 
                      size="small" 
                      onClick={copyShareUrl}
                      sx={{ ml: 1 }}
                    >
                      <ContentCopyIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </Box>
            )}
            
            {/* Download Progress and Retry */}
            {isDownloading && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" gutterBottom>
                  Download in corso...
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={downloadProgress} 
                  sx={{ mb: 1 }}
                />
                <Typography variant="body2" color="text.secondary">
                  {downloadProgress}% completato
                </Typography>
              </Box>
            )}
            
            {downloadError && (
              <Alert 
                severity="error" 
                sx={{ mt: 2 }}
                action={
                  <Button 
                    color="inherit" 
                    size="small" 
                    onClick={() => handleDownload('docx')}
                  >
                    Riprova
                  </Button>
                }
              >
                {downloadError}
              </Alert>
            )}
          </Paper>
        </Grid>
      </Grid>
      
      {/* Success Notification */}
      <Snackbar
        open={showShareSuccess}
        autoHideDuration={3000}
        onClose={handleCloseShareNotification}
        message="Link copiato negli appunti!"
      />

      {reportId && (
        <ShareButton
          documentId={reportId}
          disabled={!reportId || isLoading || isDownloading}
        />
      )}
    </Container>
  );
};

export default EnhancedReportDownloader;