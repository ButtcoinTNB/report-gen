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
  DialogActions,
  Select,
  MenuItem,
  FormControl,
  InputLabel
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
  Close as CloseIcon,
  Send as SendIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  FormatPaint as FormatIcon,
  Description as DocIcon
} from '@mui/icons-material';
import { logger } from '../utils/logger';
import { reportService, ReportVersion } from '../services/api/ReportService';
import { formatDistanceToNow } from 'date-fns';
import { it } from 'date-fns/locale';
import { diffLines } from 'diff';
import { useTask } from '../context/TaskContext';
import { useErrorHandler } from '../hooks/useErrorHandler';
import apiClient from '../services/api';

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
  onRefinementSubmit?: (instructions: string) => void;
  onDownload?: (format: 'docx' | 'pdf') => void;
}

export function DocxPreviewEditor({ 
  initialContent = '', 
  downloadUrl = '',
  reportId = '',
  showRefinementOptions = true,
  onRefinementComplete,
  onRefinementSubmit,
  onDownload
}: DocxPreviewEditorProps) {
  const { task, updateStage, updateMetrics, setReportId } = useTask();
  const { handleError, wrapPromise } = useErrorHandler();
  
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

  // Get actual report ID from props or task context
  const effectiveReportId = reportId || task.reportId;
  
  // Update content when initialContent prop changes
  useEffect(() => {
    if (initialContent) {
      setContent(initialContent);
    }
  }, [initialContent]);

  // Check for missing reportId if refinement options are shown
  useEffect(() => {
    if (showRefinementOptions && !effectiveReportId) {
      setMissingReportIdWarning(true);
      logger.warn('DocxPreviewEditor: reportId is missing but refinement options are enabled');
    } else {
      setMissingReportIdWarning(false);
    }
  }, [showRefinementOptions, effectiveReportId]);

  // Load version history when reportId is available
  const loadVersionHistory = useCallback(async () => {
    if (!effectiveReportId) return;
    
    setLoadingVersions(true);
    setError(null);
    
    try {
      const versionData = await reportService.getReportVersions(effectiveReportId);
      setVersions(versionData.versions);
    } catch (err) {
      logger.error('Error loading version history:', err);
      setError('Impossibile caricare la cronologia delle versioni. Riprova più tardi.');
    } finally {
      setLoadingVersions(false);
    }
  }, [effectiveReportId]);

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
    if (!effectiveReportId) {
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
        effectiveReportId,
        content,
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
    if (!effectiveReportId) {
      setError('ID del report mancante. Impossibile ripristinare la versione.');
      return;
    }
    
    setIsReverting(true);
    setError(null);
    
    try {
      // Revert to the selected version
      const result = await reportService.revertToVersion(effectiveReportId, version.version_number);
      
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
    setShowCompareDialog(true);
  };

  const handleDownload = (format: 'docx' | 'pdf') => {
    if (!effectiveReportId) return;
    
    try {
      // Use the reportService to download the file
      reportService.downloadReport(effectiveReportId, format, (progress) => {
        logger.info(`Download progress: ${progress}%`);
      });
      
      // Call the onDownload callback if provided
      onDownload?.(format);
    } catch (error) {
      handleError(error);
    }
  };

  const handleRefine = async () => {
    if (!refinementInstructions.trim()) {
      setError('Per favore, inserisci le istruzioni per migliorare il report.');
      return;
    }

    if (!effectiveReportId) {
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

      // Use the ReportService to start the refinement
      const { task_id } = await reportService.refineReport(
        effectiveReportId,
        content,
        refinementInstructions
      );
      
      // Set up event source for real-time updates
      const unsubscribe = reportService.subscribeToTaskEvents(
        task_id,
        (data) => {
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
            const result = data.result;
            
            if (result.draft) {
              setContent(result.draft);
              setRefinementInstructions('');
              setSuccessMessage('Report migliorato con successo!');
              setShowSuccess(true);
              setRefinementFeedback(result.feedback || null);
              
              // Update task information
              updateMetrics({
                progress: 100,
                message: 'Report migliorato con successo'
              });
              
              // Move to next stage if defined in workflow
              if (task.stage === 'refinement') {
                updateStage('formatting', 'Passaggio alla formattazione del report');
              }
              
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
              loadVersionHistory();
              
              logger.info('Report refined successfully');
              
              // Close the event source
              unsubscribe();
            }
          }
          
          // Handle task failure
          if (data.status === 'failed') {
            setError(data.error || 'Failed to refine report. Please try again.');
            setProgressMessage('');
            unsubscribe();
          }
        },
        (error) => {
          logger.error('Error in task events:', error);
          setError('Connection to event source failed. Please try again.');
          setProgressMessage('');
          setIsRefining(false);
        }
      );
      
      // Set a safety timeout
      const refinementTimeout = setTimeout(() => {
        unsubscribe();
        if (isRefining) {
          setError('Task timed out after 10 minutes. Please try again.');
          setProgressMessage('');
          setIsRefining(false);
        }
      }, 10 * 60 * 1000);
      
      // Clean up timeout if component unmounts
      return () => {
        clearTimeout(refinementTimeout);
        unsubscribe();
      };
    } catch (error) {
      logger.error('Error refining report:', error);
      setError(error instanceof Error ? error.message : 'Failed to refine report. Please try again.');
      setProgressMessage('');
      setIsRefining(false);
    }
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
          {effectiveReportId && (
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
            disabled={isLoading || !effectiveReportId}
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
                          onClick={() => handleRevertToVersion(version)}
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
              disabled={isRefining || refinementInstructions.trim().length === 0 || !effectiveReportId}
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
          onClick={() => handleDownload('docx')}
          disabled={isLoading || !effectiveReportId}
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