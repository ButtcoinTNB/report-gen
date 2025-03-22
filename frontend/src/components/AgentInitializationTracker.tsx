import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  LinearProgress, 
  Button, 
  CircularProgress,
  Stack, 
  Alert,
  AlertTitle,
  Chip,
  Collapse,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Psychology as AgentIcon,
  Cancel as CancelIcon,
  PendingActions as PendingIcon,
  CloudSync as SyncIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  AccessTime as TimeIcon
} from '@mui/icons-material';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { cancelAgentLoop } from '../store/reportSlice';
import { reportService } from '../services/api/ReportService';
import { logger } from '../utils/logger';

export interface AgentInitializationTrackerProps {
  variant?: 'compact' | 'full';
  showDetails?: boolean;
}

/**
 * A component to track and display agent loop initialization progress
 */
const AgentInitializationTracker: React.FC<AgentInitializationTrackerProps> = ({
  variant = 'full',
  showDetails = false
}) => {
  const dispatch = useAppDispatch();
  const { agentLoop } = useAppSelector(state => state.report);
  const [expanded, setExpanded] = useState(showDetails);
  const [elapsedTime, setElapsedTime] = useState(0);
  
  // Track elapsed time
  useEffect(() => {
    // Don't start the timer if there's no start time or if the process isn't running
    if (!agentLoop.startTime || (!agentLoop.isInitializing && !agentLoop.isRunning)) {
      // Reset elapsed time when process stops
      setElapsedTime(0);
      return;
    }
    
    // Calculate initial elapsed time (in case component is mounted after the process started)
    setElapsedTime(Math.floor((Date.now() - agentLoop.startTime) / 1000));
    
    // Set up interval for updating elapsed time
    const interval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - agentLoop.startTime!) / 1000));
    }, 1000);
    
    // Clean up the interval on component unmount or when process stops
    return () => {
      clearInterval(interval);
    };
  }, [agentLoop.startTime, agentLoop.isInitializing, agentLoop.isRunning]);
  
  // Format elapsed time as mm:ss
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };
  
  // Only render if there's agent loop activity
  const shouldRender = agentLoop.isInitializing || 
                       agentLoop.isRunning || 
                       agentLoop.stage === 'error' ||
                       agentLoop.progress > 0;
  
  if (!shouldRender) return null;
  
  // Handle cancellation of the agent loop
  const handleCancel = async () => {
    if (!agentLoop.taskId || !agentLoop.canCancel) return;
    
    try {
      logger.info('Cancelling agent loop task:', agentLoop.taskId);
      await reportService.cancelAgentLoop(agentLoop.taskId);
      dispatch(cancelAgentLoop());
    } catch (error) {
      logger.error('Error cancelling agent loop:', error);
      // Even if the API call fails, update the UI to show cancelled state
      dispatch(cancelAgentLoop());
    }
  };
  
  // Get appropriate icon for current stage
  const getStageIcon = () => {
    switch (agentLoop.stage) {
      case 'initializing':
        return <PendingIcon />;
      case 'writing':
      case 'reviewing':
        return <AgentIcon />;
      case 'complete':
        return <SyncIcon />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <PendingIcon />;
    }
  };
  
  // Format estimated time remaining
  const formatEstimatedTime = () => {
    if (!agentLoop.estimatedTimeRemaining) return 'Calcolo in corso...';
    
    const minutes = Math.floor(agentLoop.estimatedTimeRemaining / 60);
    const seconds = agentLoop.estimatedTimeRemaining % 60;
    
    if (minutes > 0) {
      return `${minutes} min ${seconds} sec`;
    }
    
    return `${seconds} secondi`;
  };
  
  // For compact variant, show a minimal version
  if (variant === 'compact') {
    return (
      <Box sx={{ width: '100%', mt: 1, mb: 1 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          {(agentLoop.isInitializing || agentLoop.isRunning) ? (
            <>
              <CircularProgress 
                size={16} 
                sx={{ mr: 1 }} 
              />
              <Typography variant="caption" color="text.secondary">
                {agentLoop.message}
              </Typography>
              {agentLoop.canCancel && (
                <IconButton 
                  size="small" 
                  onClick={handleCancel}
                  sx={{ ml: 'auto' }}
                >
                  <CancelIcon fontSize="small" />
                </IconButton>
              )}
            </>
          ) : agentLoop.stage === 'error' ? (
            <Alert severity="error" sx={{ py: 0 }}>
              {agentLoop.error || 'Errore durante l\'inizializzazione'}
            </Alert>
          ) : agentLoop.stage === 'complete' ? (
            <Alert severity="success" sx={{ py: 0 }}>
              Inizializzazione completata
            </Alert>
          ) : null}
        </Stack>
      </Box>
    );
  }
  
  // Full variant
  return (
    <Paper 
      elevation={2} 
      sx={{ 
        p: 2, 
        my: 2,
        borderRadius: 2,
        bgcolor: agentLoop.stage === 'error' ? 'error.lighter' : 'background.paper',
        transition: 'background-color 0.3s ease'
      }}
    >
      <Stack spacing={2}>
        {/* Header with status */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {getStageIcon()}
            <Typography variant="body1" fontWeight="medium" sx={{ ml: 1 }}>
              {agentLoop.stage === 'initializing' ? 'Inizializzazione Agenti AI' :
               agentLoop.stage === 'writing' ? 'Scrittura Report' :
               agentLoop.stage === 'reviewing' ? 'Revisione Report' :
               agentLoop.stage === 'complete' ? 'Generazione Completata' :
               agentLoop.stage === 'error' ? 'Errore Inizializzazione' :
               'Preparazione Sistema'}
            </Typography>
          </Box>
          
          {/* Elapsed time */}
          {(agentLoop.isInitializing || agentLoop.isRunning) && agentLoop.startTime && (
            <Chip 
              icon={<TimeIcon />}
              label={formatTime(elapsedTime)}
              size="small"
              color="primary"
              variant="outlined"
            />
          )}
        </Box>
        
        {/* Progress bar */}
        <Box sx={{ width: '100%' }}>
          <LinearProgress 
            variant="determinate" 
            value={agentLoop.progress} 
            sx={{ 
              height: 8, 
              borderRadius: 4,
              bgcolor: agentLoop.stage === 'error' ? 'error.lighter' : undefined
            }}
            color={agentLoop.stage === 'error' ? 'error' : 'primary'}
          />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              {agentLoop.message}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {agentLoop.progress}%
            </Typography>
          </Box>
        </Box>
        
        {/* Iteration info when running */}
        {agentLoop.isRunning && agentLoop.stage !== 'initializing' && (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Iterazione {agentLoop.currentIteration}/{agentLoop.totalIterations}
            </Typography>
          </Box>
        )}
        
        {/* Error message */}
        {agentLoop.error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            <AlertTitle>Errore durante l'inizializzazione</AlertTitle>
            <Box sx={{ mb: 1 }}>
              {agentLoop.error}
            </Box>
            
            {/* Recovery guidance based on error type */}
            <Box sx={{ mt: 2, fontSize: '0.9rem' }}>
              {agentLoop.error.includes('network') || agentLoop.error.includes('connessione') ? (
                <>
                  <Typography variant="subtitle2" fontWeight="bold">
                    Suggerimento:
                  </Typography>
                  <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem' }}>
                    <li>Controlla la tua connessione a Internet</li>
                    <li>Riprova tra qualche istante</li>
                    <li>Se il problema persiste, contatta l'assistenza</li>
                  </ul>
                </>
              ) : agentLoop.error.includes('timeout') || agentLoop.error.includes('tempo') ? (
                <>
                  <Typography variant="subtitle2" fontWeight="bold">
                    Suggerimento:
                  </Typography>
                  <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem' }}>
                    <li>Il server potrebbe essere sovraccarico</li>
                    <li>Riprova più tardi quando il sistema è meno occupato</li>
                    <li>Se stai elaborando file di grandi dimensioni, considera di dividerli in parti più piccole</li>
                  </ul>
                </>
              ) : agentLoop.error.includes('permission') || agentLoop.error.includes('autorizzazione') ? (
                <>
                  <Typography variant="subtitle2" fontWeight="bold">
                    Suggerimento:
                  </Typography>
                  <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem' }}>
                    <li>Verifica di avere le autorizzazioni necessarie</li>
                    <li>Prova a effettuare nuovamente l'accesso</li>
                    <li>Contatta l'amministratore per assistenza</li>
                  </ul>
                </>
              ) : agentLoop.error.includes('cancelled') || agentLoop.error.includes('annullat') ? (
                <>
                  <Typography variant="subtitle2" fontWeight="bold">
                    Informazione:
                  </Typography>
                  <p style={{ margin: '0.5rem 0' }}>
                    Il processo è stato annullato. Puoi ricominciare quando preferisci.
                  </p>
                </>
              ) : (
                <>
                  <Typography variant="subtitle2" fontWeight="bold">
                    Azioni possibili:
                  </Typography>
                  <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem' }}>
                    <li>Riprova l'operazione</li>
                    <li>Verifica che i documenti caricati siano nel formato corretto</li>
                    <li>Se il problema persiste, contatta l'assistenza tecnica</li>
                  </ul>
                </>
              )}
            </Box>
            
            {/* Technical details section */}
            {agentLoop.error.includes('technical:') && (
              <Box sx={{ mt: 1, pt: 1, borderTop: '1px solid rgba(0,0,0,0.1)', fontSize: '0.8rem', color: 'text.secondary' }}>
                <Typography variant="caption" component="p">
                  Dettagli tecnici:
                </Typography>
                <code style={{ display: 'block', padding: '0.5rem', background: 'rgba(0,0,0,0.05)', borderRadius: '4px', overflowX: 'auto', fontSize: '0.7rem' }}>
                  {agentLoop.error.split('technical:')[1].trim()}
                </code>
              </Box>
            )}
          </Alert>
        )}
        
        {/* Time estimate */}
        {(agentLoop.isInitializing || agentLoop.isRunning) && agentLoop.estimatedTimeRemaining !== null && (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <TimeIcon fontSize="small" sx={{ mr: 1, opacity: 0.6 }} />
            <Typography variant="body2" color="text.secondary">
              Tempo stimato rimanente: {formatEstimatedTime()}
            </Typography>
          </Box>
        )}
        
        {/* Action buttons */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {/* Cancellation button */}
          {agentLoop.canCancel && (agentLoop.isInitializing || agentLoop.isRunning) && (
            <Button
              variant="outlined"
              color="secondary"
              startIcon={<CancelIcon />}
              onClick={handleCancel}
              size="small"
            >
              Annulla
            </Button>
          )}
          
          {/* Details toggle */}
          <Tooltip title={expanded ? 'Nascondi dettagli' : 'Mostra dettagli'}>
            <IconButton size="small" onClick={() => setExpanded(!expanded)} sx={{ ml: 'auto' }}>
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Tooltip>
        </Box>
        
        {/* Expanded technical details */}
        <Collapse in={expanded}>
          <Paper variant="outlined" sx={{ p: 1.5 }}>
            <Typography variant="caption" color="text.secondary" component="div">
              <Box sx={{ mb: 0.5 }}>
                <strong>Task ID:</strong> {agentLoop.taskId || 'N/A'}
              </Box>
              <Box sx={{ mb: 0.5 }}>
                <strong>Stato:</strong> {agentLoop.stage}
              </Box>
              <Box sx={{ mb: 0.5 }}>
                <strong>Tempo trascorso:</strong> {formatTime(elapsedTime)}
              </Box>
              {agentLoop.startTime && (
                <Box>
                  <strong>Avviato:</strong> {new Date(agentLoop.startTime).toLocaleTimeString()}
                </Box>
              )}
            </Typography>
          </Paper>
        </Collapse>
      </Stack>
    </Paper>
  );
};

export default AgentInitializationTracker; 