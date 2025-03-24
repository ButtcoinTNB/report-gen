"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  Box, 
  Button, 
  TextField, 
  CircularProgress, 
  Alert,
  Snackbar,
  Typography,
  Divider,
  Paper,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemButton,
  IconButton,
  Collapse,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { 
  Download as DownloadIcon, 
  Refresh as RefreshIcon, 
  History as HistoryIcon,
  RestoreOutlined as RestoreIcon,
  PersonOutline as UserIcon,
  SmartToy as AIIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Compare as CompareIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import { logger } from '../utils/logger';
import { reportService, ReportVersion } from '../services/api/ReportService';
import { formatDistanceToNow } from 'date-fns';
import { it } from 'date-fns/locale';
import { diffLines } from 'diff';

interface DocxPreviewEditorProps {
  initialContent?: string;
  downloadUrl?: string;
  reportId?: string;
  showRefinementOptions?: boolean;
  onRefinementComplete?: (data: { 
    draft: string;
    feedback: { score: number; suggestions: string[] };
    iterations: number;
    docx_url?: string;
  }) => void;
}

export function DocxPreviewEditor({ 
  initialContent = '', 
  downloadUrl = '',
  reportId = '',
  showRefinementOptions = true,
  onRefinementComplete 
}: DocxPreviewEditorProps) {
  const [content, setContent] = useState(initialContent || '');
  const [refinementInstructions, setRefinementInstructions] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRefining, setIsRefining] = useState(false);
  const [refinementProgress, setRefinementProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [refinementFeedback, setRefinementFeedback] = useState<{score: number; suggestions: string[]} | null>(null);
  const [missingReportIdWarning, setMissingReportIdWarning] = useState(false);
  
  // Version history related states
  const [versions, setVersions] = useState<ReportVersion[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<ReportVersion | null>(null);
  const [isReverting, setIsReverting] = useState(false);
  const [showCompareDialog, setShowCompareDialog] = useState(false);
  const [compareContent, setCompareContent] = useState<{current: string, selected: string}>({
    current: '',
    selected: ''
  });

  // Update content when initialContent prop changes
  useEffect(() => {
    if (initialContent) {
      setContent(initialContent);
    }
  }, [initialContent]);

  // Check for missing reportId if refinement options are shown
  useEffect(() => {
    if (showRefinementOptions && !reportId) {
      setMissingReportIdWarning(true);
      logger.warn('DocxPreviewEditor: reportId is missing but refinement options are enabled');
    } else {
      setMissingReportIdWarning(false);
    }
  }, [showRefinementOptions, reportId]);

  // Load version history when reportId is available
  const loadVersionHistory = useCallback(async () => {
    if (!reportId) return;
    
    setLoadingVersions(true);
    setError(null);
    
    try {
      const versionData = await reportService.getReportVersions(reportId);
      setVersions(versionData.versions);
    } catch (err) {
      logger.error('Error loading version history:', err);
      setError('Impossibile caricare la cronologia delle versioni. Riprova più tardi.');
    } finally {
      setLoadingVersions(false);
    }
  }, [reportId]);

  useEffect(() => {
    if (showVersionHistory) {
      loadVersionHistory();
    }
  }, [showVersionHistory, loadVersionHistory]);

  // Format a date relative to now (e.g., "2 hours ago")
  const formatRelativeDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return formatDistanceToNow(date, { addSuffix: true, locale: it });
    } catch (error) {
      return 'Data sconosciuta';
    }
  };

  // Handle manual content update with version tracking
  const handleUpdateContent = async () => {
    if (!reportId) {
      setError('ID del report mancante. Impossibile salvare le modifiche.');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Create a version description prompt dialog
      const description = window.prompt('Inserisci una breve descrizione delle modifiche apportate (opzionale)');
      
      // Update the report with a new version
      await reportService.updateReportWithVersion(
        reportId,
        { content },
        true, // create a new version
        description || 'Modifiche manuali'
      );
      
      setSuccessMessage('Modifiche salvate con successo!');
      setShowSuccess(true);
      
      // Reload the version history
      await loadVersionHistory();
    } catch (err) {
      logger.error('Error updating report content:', err);
      setError('Impossibile salvare le modifiche. Riprova più tardi.');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle reverting to a previous version
  const handleRevertToVersion = async (version: ReportVersion) => {
    if (!reportId) {
      setError('ID del report mancante. Impossibile ripristinare la versione.');
      return;
    }
    
    setIsReverting(true);
    setError(null);
    
    try {
      // Revert to the selected version
      const result = await reportService.revertToVersion(reportId, version.version_number);
      
      // Update the content in the editor
      setContent(result.content);
      
      setSuccessMessage(`Versione ${version.version_number} ripristinata con successo!`);
      setShowSuccess(true);
      
      // Reload the version history
      await loadVersionHistory();
      
      // Close the version history panel
      setSelectedVersion(null);
    } catch (err) {
      logger.error('Error reverting to version:', err);
      setError(`Impossibile ripristinare la versione ${version.version_number}. Riprova più tardi.`);
    } finally {
      setIsReverting(false);
    }
  };

  // Open the compare dialog to show differences
  const handleCompareVersion = (version: ReportVersion) => {
    setCompareContent({
      current: content,
      selected: version.content
    });
    setCompareDialogOpen(true);
  };

  const handleDownload = async () => {
    setIsLoading(true);
    setError(null);

    try {
      logger.info('Generating DOCX file...');

      // Check if we have a downloadUrl
      if (!downloadUrl) {
        throw new Error('URL di download non disponibile. Impossibile generare il documento.');
      }

      const response = await fetch('/api/generate-docx', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to generate document');
      }

      // Trigger download
      window.location.href = downloadUrl;
      setSuccessMessage('File DOCX generato con successo!');
      setShowSuccess(true);
      logger.info('DOCX file generated successfully');

    } catch (error) {
      logger.error('Error generating DOCX:', error);
      setError(error instanceof Error ? error.message : 'Failed to generate document. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefine = async () => {
    if (!refinementInstructions.trim()) {
      setError('Per favore, inserisci le istruzioni per migliorare il report.');
      return;
    }

    if (!reportId) {
      setError('ID del report mancante. Impossibile procedere con il miglioramento.');
      setMissingReportIdWarning(true);
      return;
    }

    setIsRefining(true);
    setRefinementProgress(0);
    setProgressMessage('Inizializzazione...');
    setError(null);

    try {
      logger.info('Submitting refinement request...');

      // Start the refinement task in the background
      const startResponse = await fetch('/api/agent-loop/refine-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          report_id: reportId,
          content: content,
          instructions: refinementInstructions 
        }),
      });

      if (!startResponse.ok) {
        const errorData = await startResponse.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to start refinement');
      }

      const { task_id } = await startResponse.json();
      
      // Connect to SSE endpoint for real-time updates
      const result = await subscribeToTaskEvents(task_id);
      
      if (result.draft) {
        setContent(result.draft);
        setRefinementInstructions('');
        setSuccessMessage('Report migliorato con successo!');
        setShowSuccess(true);
        setRefinementFeedback(result.feedback || null);
        
        if (onRefinementComplete) {
          onRefinementComplete(result);
        }
        
        // Show "from cache" indicator if the result was cached
        if (result.from_cache) {
          setProgressMessage('Miglioramento veloce (pattern in cache)');
        } else {
          setProgressMessage('');
        }
        
        // Reload version history after AI refinement
        await loadVersionHistory();
        
        logger.info('Report refined successfully');
      } else {
        throw new Error('Invalid response format: missing draft content');
      }
    } catch (error) {
      logger.error('Error refining report:', error);
      setError(error instanceof Error ? error.message : 'Failed to refine report. Please try again.');
      setProgressMessage('');
    } finally {
      setIsRefining(false);
    }
  };

  // Use Server-Sent Events for real-time progress updates
  const subscribeToTaskEvents = (taskId: string): Promise<any> => {
    return new Promise((resolve, reject) => {
      try {
        // Open SSE connection
        const eventSource = new EventSource(`/api/agent-loop/task-events/${taskId}`);
        
        // Handle updates
        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            // Update progress in UI
            if (data.progress !== undefined) {
              setRefinementProgress(data.progress * 100);
            }
            
            // Update status message
            if (data.message) {
              setProgressMessage(data.message);
            }
            
            // Handle task completion
            if (data.status === 'completed' && data.result) {
              eventSource.close();
              resolve(data.result);
            } 
            // Handle task failure
            else if (data.status === 'failed') {
              eventSource.close();
              reject(new Error(data.error || 'Task failed'));
            }
            // Handle expired tasks
            else if (data.status === 'expired') {
              eventSource.close();
              reject(new Error('Task expired or was removed'));
            }
          } catch (err) {
            logger.error('Error parsing event data:', err);
          }
        };
        
        // Handle connection errors
        eventSource.onerror = (error) => {
          eventSource.close();
          reject(new Error('Connection to event source failed'));
        };
        
        // Safety timeout (10 minutes)
        const timeout = setTimeout(() => {
          eventSource.close();
          reject(new Error('Task timed out after 10 minutes'));
        }, 10 * 60 * 1000);
        
        // Clean up timeout on completion
        eventSource.addEventListener('close', () => {
          clearTimeout(timeout);
        });
        
      } catch (error) {
        reject(error);
      }
    });
  };

  // Simple diff function to highlight added/removed content
  const generateDiff = (original: string, modified: string) => {
    const lines1 = original.split('\n');
    const lines2 = modified.split('\n');
    const result: JSX.Element[] = [];
    
    // Very simple line-by-line diff visualization
    // A more sophisticated diff algorithm would be better for production
    for (let i = 0; i < Math.max(lines1.length, lines2.length); i++) {
      const line1 = lines1[i] || '';
      const line2 = lines2[i] || '';
      
      if (line1 === line2) {
        result.push(<div key={i}>{line1}</div>);
      } else {
        result.push(
          <div key={i} style={{ display: 'flex', marginBottom: '8px' }}>
            <div style={{ backgroundColor: '#ffecec', textDecoration: 'line-through', flex: 1, padding: '4px', marginRight: '8px', color: '#ff0000' }}>
              {line1}
            </div>
            <div style={{ backgroundColor: '#eaffea', flex: 1, padding: '4px', color: '#008000' }}>
              {line2}
            </div>
          </div>
        );
      }
    }
    
    return result;
  };

  return (
    <Box sx={{ width: '100%' }}>
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {missingReportIdWarning && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Avviso: ID report mancante. La funzionalità di miglioramento non sarà disponibile.
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Editor Report</Typography>
        <Box>
          {reportId && (
            <Tooltip title="Cronologia versioni">
              <IconButton 
                color={showVersionHistory ? 'primary' : 'default'} 
                onClick={() => setShowVersionHistory(!showVersionHistory)}
                disabled={loadingVersions}
              >
                {loadingVersions ? <CircularProgress size={24} /> : <HistoryIcon />}
              </IconButton>
            </Tooltip>
          )}
          <Button
            variant="outlined"
            color="primary"
            onClick={handleUpdateContent}
            disabled={isLoading || !reportId}
            sx={{ ml: 1 }}
          >
            Salva versione
          </Button>
        </Box>
      </Box>

      {showVersionHistory && (
        <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Cronologia Versioni
          </Typography>
          {versions.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              Nessuna versione precedente disponibile.
            </Typography>
          ) : (
            <List sx={{ maxHeight: '300px', overflowY: 'auto' }}>
              {versions.map((version) => (
                <ListItem 
                  key={version.version_id}
                  secondaryAction={
                    <Box>
                      <Tooltip title="Confronta con versione attuale">
                        <IconButton 
                          edge="end" 
                          aria-label="compare" 
                          onClick={() => handleCompareVersion(version)}
                        >
                          <CompareIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Ripristina questa versione">
                        <IconButton 
                          edge="end" 
                          aria-label="restore" 
                          onClick={() => handleRevertToVersion(version.version_number)}
                          disabled={isReverting}
                          sx={{ ml: 1 }}
                        >
                          {isReverting ? <CircularProgress size={24} /> : <RestoreIcon />}
                        </IconButton>
                      </Tooltip>
                    </Box>
                  }
                  disablePadding
                >
                  <ListItemButton 
                    onClick={() => 
                      setSelectedVersion(selectedVersion?.version_id === version.version_id ? null : version)
                    }
                  >
                    <ListItemIcon>
                      {version.created_by_ai ? <AIIcon color="primary" /> : <UserIcon />}
                    </ListItemIcon>
                    <ListItemText 
                      primary={
                        <Typography variant="body1">
                          Versione {version.version_number}
                          {version.created_by_ai && ' (AI)'}
                        </Typography>
                      }
                      secondary={
                        <>
                          <Typography variant="caption" display="block">
                            {formatRelativeDate(version.created_at)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" noWrap>
                            {version.changes_description || 'Nessuna descrizione'}
                          </Typography>
                        </>
                      }
                    />
                    {selectedVersion?.version_id === version.version_id ? 
                      <ExpandLessIcon /> : <ExpandMoreIcon />}
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          )}
        </Paper>
      )}

      <TextField
        fullWidth
        multiline
        rows={15}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        sx={{
          mb: 3,
          '& .MuiInputBase-root': {
            fontFamily: 'monospace',
            fontSize: '0.9rem'
          }
        }}
      />
      
      {refinementFeedback && (
        <Paper elevation={2} sx={{ p: 2, mb: 3, bgcolor: 'background.subtle' }}>
          <Typography variant="h6" gutterBottom>
            Feedback AI
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography variant="body2" sx={{ mr: 1 }}>
              Qualità del report:
            </Typography>
            <Box 
              sx={{ 
                width: '100%', 
                height: 10, 
                bgcolor: 'grey.300', 
                borderRadius: 5,
                overflow: 'hidden'
              }}
            >
              <Box 
                sx={{ 
                  width: `${refinementFeedback.score * 100}%`, 
                  height: '100%', 
                  bgcolor: refinementFeedback.score > 0.8 ? 'success.main' : 
                            refinementFeedback.score > 0.6 ? 'warning.main' : 'error.main',
                }}
              />
            </Box>
            <Typography variant="body2" sx={{ ml: 1, fontWeight: 'bold' }}>
              {Math.round(refinementFeedback.score * 100)}%
            </Typography>
          </Box>
          
          {refinementFeedback.suggestions.length > 0 && (
            <>
              <Typography variant="subtitle2" gutterBottom>
                Suggerimenti per ulteriori miglioramenti:
              </Typography>
              <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                {refinementFeedback.suggestions.map((suggestion, i) => (
                  <li key={i}>
                    <Typography variant="body2">{suggestion}</Typography>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Paper>
      )}
      
      {showRefinementOptions && (
        <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Migliora il Report con l'AI
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Descrivi cosa vorresti migliorare o correggere nel report. L'AI aggiornerà il contenuto in base alle tue istruzioni.
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={3}
            placeholder="Es. Aggiungi più dettagli sulla causa del danno, correggi il totale, migliora la struttura..."
            value={refinementInstructions}
            onChange={(e) => setRefinementInstructions(e.target.value)}
            sx={{ mb: 2 }}
            helperText={`${refinementInstructions.length}/500 caratteri - Sii specifico nelle tue istruzioni per ottenere i migliori risultati`}
            InputProps={{
              endAdornment: (
                <Box sx={{ position: 'absolute', right: 8, bottom: 8, color: 'text.secondary' }}>
                  {refinementInstructions.length > 0 && (
                    <Typography variant="caption">
                      {refinementInstructions.length}/500
                    </Typography>
                  )}
                </Box>
              ),
            }}
          />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              Esempi: "Aggiungi una sezione sul metodo di calcolo", "Riformula il paragrafo su..."
            </Typography>
            <Button
              variant="outlined"
              color="primary"
              onClick={handleRefine}
              disabled={isRefining || refinementInstructions.trim().length === 0 || !reportId}
              startIcon={isRefining ? <CircularProgress size={20} /> : <RefreshIcon />}
            >
              {isRefining ? 
                refinementProgress > 0 ? 
                  `Miglioramento in corso... ${Math.round(refinementProgress)}%` : 
                  'Miglioramento in corso...' 
                : 'Migliora Report'}
            </Button>
          </Box>
        </Paper>
      )}
      
      {isRefining && (
        <Box sx={{ width: '100%', mt: 2 }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            {progressMessage || 'Elaborazione in corso...'}
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={refinementProgress} 
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>
      )}
      
      <Divider sx={{ mb: 3 }} />
      
      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleDownload}
          disabled={isLoading || !downloadUrl}
          startIcon={isLoading ? <CircularProgress size={20} /> : <DownloadIcon />}
        >
          {isLoading ? 'Generazione...' : 'Scarica DOCX'}
        </Button>
      </Box>

      <Snackbar
        open={showSuccess}
        autoHideDuration={6000}
        onClose={() => setShowSuccess(false)}
      >
        <Alert severity="success" sx={{ width: '100%' }}>
          {successMessage}
        </Alert>
      </Snackbar>

      {/* Compare dialog for showing differences between versions */}
      <Dialog
        open={showCompareDialog}
        onClose={() => setShowCompareDialog(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>Confronto Versioni</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ maxHeight: '500px', overflowY: 'auto' }}>
            {generateDiff(compareContent.selected, compareContent.current)}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCompareDialog(false)}>Chiudi</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
} 