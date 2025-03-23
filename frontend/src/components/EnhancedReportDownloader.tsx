import React, { useState, useEffect, useCallback } from 'react';
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
  Snackbar
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import ShareIcon from '@mui/icons-material/Share';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { RootState } from '../store';
import { setLoading, setError, setPreviewUrl as setStorePreviewUrl } from '../store/reportSlice';
import { DocumentPreview, DownloadProgressTracker, ReportSummary } from './DynamicComponents';
import { isBrowser } from '../utils/environment';
import supabase, { queryCached, clearCache, DocumentMetadata, documentService } from '../utils/supabase';
import { config } from '../../config';

/**
 * Enhanced Report Downloader component that combines document preview,
 * report metrics, and download functionality in a single interface
 */
const EnhancedReportDownloader: React.FC = () => {
  const dispatch = useAppDispatch();
  
  // Get state from Redux
  const { reportId, content, previewUrl, loading, error: storeError } = useAppSelector(
    (state: RootState) => state.report
  );
  
  // Local state
  const [downloadProgress, setDownloadProgress] = useState<number>(0);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>('report.docx');
  const [fileSize, setFileSize] = useState<number>(0);
  const [shareUrl, setShareUrl] = useState<string>('');
  const [showShareSuccess, setShowShareSuccess] = useState<boolean>(false);
  const [qualityScore, setQualityScore] = useState<number>(0);
  const [editCount, setEditCount] = useState<number>(0);
  const [iterations, setIterations] = useState<number>(0);
  const [timeSaved, setTimeSaved] = useState<number>(120); // Default 2 hours
  const [downloadReady, setDownloadReady] = useState<boolean>(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [documentData, setDocumentData] = useState<DocumentMetadata | null>(null);
  const [totalPages, setTotalPages] = useState<number>(1);
  
  // Get document metadata when component mounts
  useEffect(() => {
    if (reportId) {
      fetchDocumentMetadata(reportId);
    }
    
    // Cleanup function to abort any in-progress requests
    return () => {
      if (abortController) {
        abortController.abort();
      }
    };
  }, [reportId]);
  
  // Generate preview
  const handleGeneratePreview = async () => {
    if (!reportId) return;
    
    try {
      dispatch(setLoading(true));
      
      // Generate preview using document service
      const url = await documentService.generatePreview(reportId);
      
      // Update both local state and Redux store
      dispatch(setStorePreviewUrl(url));
      setPreviewError(null);
    } catch (err) {
      console.error('Error generating preview:', err);
      setPreviewError(err instanceof Error ? err.message : 'Impossibile generare l\'anteprima');
      dispatch(setError(err instanceof Error ? err.message : 'Impossibile generare l\'anteprima'));
    } finally {
      dispatch(setLoading(false));
    }
  };
  
  // Fetch document metadata from Supabase
  const fetchDocumentMetadata = useCallback(async (documentId: string) => {
    setIsLoading(true);
    setError(null);
    dispatch(setLoading(true));
    
    try {
      // Use cached query for document metadata with a 5-minute cache
      const { data, error } = await queryCached(
        'documents',
        { 
          select: '*',
          filter: { id: documentId },
          single: true
        },
        300 // 5 minutes cache
      );
      
      if (error) throw error;
      
      if (!data) {
        throw new Error('Documento non trovato');
      }
      
      // Update all relevant state with the document data
      setDocumentData(data as DocumentMetadata);
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
      setError(error instanceof Error ? error.message : 'Errore nel recupero dei dati del documento');
      dispatch(setError(error instanceof Error ? error.message : 'Errore nel recupero dei dati del documento'));
    } finally {
      setIsLoading(false);
      dispatch(setLoading(false));
    }
  }, [dispatch, handleGeneratePreview]);
  
  // Download the document with progress tracking
  const handleDownload = async (format: string = 'docx') => {
    if (!reportId) {
      dispatch(setError('Nessun ID report disponibile. Impossibile scaricare il report.'));
      return;
    }
    
    setIsDownloading(true);
    setDownloadProgress(0);
    setDownloadError(null);
    
    try {
      const downloadUrl = `${config.API_URL}/api/download/${format}/${reportId}`;
      
      // Use fetch with a ReadableStream to track download progress
      const response = await fetch(downloadUrl);
      
      if (!response.ok) {
        throw new Error(`Errore nel download: ${response.status} ${response.statusText}`);
      }
      
      // Get total file size from headers
      const contentLength = response.headers.get('content-length');
      const total = contentLength ? parseInt(contentLength, 10) : 0;
      
      // Create a reader from the response body stream
      const reader = response.body?.getReader();
      
      if (!reader) {
        throw new Error('Streaming non supportato dal browser');
      }
      
      // Initialize variables for tracking progress
      let receivedLength = 0;
      const chunks: Uint8Array[] = [];
      
      // Read the stream
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }
        
        chunks.push(value);
        receivedLength += value.length;
        
        // Update progress
        if (total > 0) {
          setDownloadProgress((receivedLength / total) * 100);
        }
      }
      
      // Concatenate chunks into a single Uint8Array
      const chunksAll = new Uint8Array(receivedLength);
      let position = 0;
      for (const chunk of chunks) {
        chunksAll.set(chunk, position);
        position += chunk.length;
      }
      
      // Create a blob from the data
      const blob = new Blob([chunksAll], { 
        type: format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
      });
      
      // Set progress to 100% before triggering download
      setDownloadProgress(100);
      
      // Create a download link
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      // Delay closing the progress modal to show 100% completion
      setTimeout(() => {
        setIsDownloading(false);
      }, 1000);
      
    } catch (err) {
      console.error('Error downloading report:', err);
      setDownloadError(err instanceof Error ? err.message : 'Impossibile scaricare il report');
      setIsDownloading(false);
    }
  };
  
  // Generate and copy share link
  const handleShareLink = async () => {
    if (!reportId) {
      dispatch(setError('Nessun ID report disponibile. Impossibile generare link di condivisione.'));
      return;
    }
    
    // Create a new AbortController for this request
    const controller = new AbortController();
    setAbortController(controller);
    
    try {
      dispatch(setLoading({
        isLoading: true,
        message: 'Generazione link di condivisione...'
      }));
      
      // Call the API to create a shareable link with abort signal
      const response = await fetch(`${config.API_URL}/api/share/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          report_id: reportId,
          expiration_days: 7 // Default to 7-day expiration
        }),
        signal: controller.signal
      });
      
      if (!response.ok) {
        throw new Error('Impossibile generare link di condivisione');
      }
      
      const data = await response.json();
      
      if (data.share_url) {
        setShareUrl(data.share_url);
        
        // Copy to clipboard only in browser environment
        if (isBrowser && navigator.clipboard) {
          try {
            await navigator.clipboard.writeText(data.share_url);
            setShowShareSuccess(true);
          } catch (clipboardErr) {
            console.error('Failed to copy to clipboard:', clipboardErr);
          }
        }
      }
      
      dispatch(setLoading({
        isLoading: false
      }));
      
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Request was aborted, do nothing
        return;
      }
      
      console.error('Error generating share link:', err);
      dispatch(setError(err instanceof Error ? err.message : 'Impossibile generare link di condivisione'));
      dispatch(setLoading({
        isLoading: false
      }));
    } finally {
      setAbortController(null);
    }
  };
  
  // Copy share URL to clipboard
  const copyShareUrl = async () => {
    if (!isBrowser || !navigator.clipboard || !shareUrl) return;
    
    try {
      await navigator.clipboard.writeText(shareUrl);
      setShowShareSuccess(true);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };
  
  // Close the share success notification
  const handleCloseShareNotification = () => {
    setShowShareSuccess(false);
  };
  
  // When a document is updated, clear the cache to ensure fresh data
  const invalidateDocumentCache = useCallback(() => {
    if (reportId) {
      const cacheKey = `supabase_documents_${JSON.stringify({
        select: '*',
        filter: { id: reportId },
        single: true
      })}`;
      
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(cacheKey);
      }
    }
  }, [reportId]);
  
  // When component unmounts, invalidate the document cache
  useEffect(() => {
    return () => {
      invalidateDocumentCache();
    };
  }, [invalidateDocumentCache]);
  
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
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Opzioni di Download
            </Typography>
            
            <Divider sx={{ mb: 2 }} />
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary" paragraph>
                Il tuo report è pronto per il download. Scegli il formato preferito.
              </Typography>
            </Box>
            
            {/* DOCX Download Card */}
            <Card variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="subtitle1" fontWeight="medium">
                  Microsoft Word (DOCX)
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Documento completamente modificabile.
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
                  Scarica DOCX
                </Button>
              </CardActions>
            </Card>
            
            {/* PDF Download Card */}
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
                  Scarica PDF
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
              <Card variant="outlined" sx={{ mb: 2, bgcolor: 'background.subtle' }}>
                <CardContent sx={{ py: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Typography variant="body2" sx={{ mr: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {shareUrl}
                    </Typography>
                    <Button
                      size="small"
                      startIcon={<ContentCopyIcon />}
                      onClick={copyShareUrl}
                    >
                      Copia
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            )}
            
            <Typography variant="caption" color="text.secondary">
              I link di condivisione scadono dopo 7 giorni per motivi di sicurezza.
            </Typography>
          </Paper>
        </Grid>
      </Grid>
      
      {/* Download Progress Tracker */}
      <DownloadProgressTracker 
        isDownloading={isDownloading}
        fileName={fileName}
        fileSize={fileSize}
        progress={downloadProgress}
        error={downloadError}
        onClose={() => setIsDownloading(false)}
        onRetry={() => handleDownload()}
      />
      
      {/* Success notification for share link copy */}
      {isBrowser && (
        <Snackbar
          open={showShareSuccess}
          autoHideDuration={4000}
          onClose={handleCloseShareNotification}
          message="Link copiato negli appunti!"
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        />
      )}
    </Container>
  );
};

export default EnhancedReportDownloader; 