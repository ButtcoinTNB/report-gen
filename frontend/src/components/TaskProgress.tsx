import React, { useMemo } from 'react';
import { 
  Box, 
  Typography, 
  LinearProgress, 
  Stepper, 
  Step, 
  StepLabel, 
  Chip, 
  Paper,
  Grid,
  Tooltip,
  CircularProgress,
  Skeleton
} from '@mui/material';
import { 
  Schedule as ScheduleIcon,
  Stars as QualityIcon,
  Loop as IterationsIcon,
  Error as ErrorIcon,
  CheckCircle as CompletedIcon,
  Cancel as CancelledIcon,
  HourglassEmpty as PendingIcon,
  Cached as InProgressIcon
} from '@mui/icons-material';
import { useTask, ProcessStage, TaskStatus } from '../context/TaskContext';
import { useErrorHandler } from '../hooks/useErrorHandler';

// Define stages display information
const stageInfo: Record<ProcessStage, {
  label: string;
  description: string;
}> = {
  idle: { 
    label: 'Inizio', 
    description: 'Pronto per iniziare' 
  },
  upload: { 
    label: 'Caricamento', 
    description: 'Caricamento documenti' 
  },
  extraction: { 
    label: 'Estrazione', 
    description: 'Estrazione dei contenuti' 
  },
  analysis: { 
    label: 'Analisi', 
    description: 'Analisi dei dati' 
  },
  writer: { 
    label: 'Scrittura', 
    description: 'Generazione report' 
  },
  reviewer: { 
    label: 'Revisione', 
    description: 'Controllo qualità' 
  },
  refinement: { 
    label: 'Perfezionamento', 
    description: 'Miglioramento report' 
  },
  formatting: { 
    label: 'Formattazione', 
    description: 'Finalizzazione layout' 
  },
  finalization: { 
    label: 'Completamento', 
    description: 'Report pronto' 
  }
};

// Ordered stages for stepper
const orderedStages: ProcessStage[] = [
  'idle',
  'upload',
  'extraction',
  'analysis',
  'writer',
  'reviewer',
  'refinement',
  'formatting',
  'finalization'
];

// Status icons and colors
const statusConfig: Record<TaskStatus, {
  icon: React.ReactElement;
  color: string;
  label: string;
}> = {
  pending: { 
    icon: <PendingIcon />, 
    color: 'info.main', 
    label: 'In attesa' 
  },
  in_progress: { 
    icon: <InProgressIcon />, 
    color: 'primary.main', 
    label: 'In corso' 
  },
  completed: { 
    icon: <CompletedIcon />, 
    color: 'success.main', 
    label: 'Completato' 
  },
  failed: { 
    icon: <ErrorIcon />, 
    color: 'error.main', 
    label: 'Fallito' 
  },
  cancelled: { 
    icon: <CancelledIcon />, 
    color: 'warning.main', 
    label: 'Annullato' 
  }
};

// Format time remaining
const formatTimeRemaining = (seconds: number): string => {
  if (seconds < 60) {
    return `${seconds} secondi`;
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    return `${minutes} ${minutes === 1 ? 'minuto' : 'minuti'}`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours} ${hours === 1 ? 'ora' : 'ore'}${minutes > 0 ? ` e ${minutes} ${minutes === 1 ? 'minuto' : 'minuti'}` : ''}`;
  }
};

const TaskProgress: React.FC = () => {
  const { task, isProcessing } = useTask();
  const { handleError } = useErrorHandler();
  
  // Calculate active step for stepper
  const activeStep = useMemo(() => {
    const index = orderedStages.findIndex(stage => stage === task.stage);
    return index === -1 ? 0 : index;
  }, [task.stage]);
  
  // Generate accessibility aria labels
  const ariaValueText = useMemo(() => {
    if (task.status === 'completed') {
      return 'Processo completato al 100%';
    } else if (task.status === 'failed') {
      return `Processo fallito: ${task.error?.message || 'Errore sconosciuto'}`;
    } else if (task.status === 'cancelled') {
      return 'Processo annullato';
    } else {
      return `${Math.round(task.progress)}% completato, fase: ${stageInfo[task.stage]?.label || task.stage}`;
    }
  }, [task.progress, task.stage, task.status, task.error]);
  
  // Show error if there is one
  const renderError = () => {
    if (!task.error) return null;
    
    return (
      <Box 
        sx={{ 
          mt: 2, 
          p: 2, 
          bgcolor: 'error.light', 
          borderRadius: 1,
          color: 'error.contrastText'
        }}
        role="alert"
      >
        <Typography variant="subtitle2" fontWeight="bold">Errore:</Typography>
        <Typography variant="body2">{task.error.message}</Typography>
      </Box>
    );
  };
  
  return (
    <Paper 
      elevation={2} 
      sx={{ p: 3, mb: 3, borderRadius: 2 }}
      aria-live="polite"
      aria-atomic="true"
    >
      {/* Status header with chip */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" component="h2" gutterBottom={false}>
          Stato del processo
        </Typography>
        
        <Chip
          icon={statusConfig[task.status].icon}
          label={statusConfig[task.status].label}
          sx={{ 
            bgcolor: statusConfig[task.status].color,
            color: 'white',
            fontWeight: 'medium'
          }}
        />
      </Box>
      
      {/* Current stage and message */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="subtitle1" color="primary.main" fontWeight="medium">
          {stageInfo[task.stage]?.label || task.stage}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {task.message || stageInfo[task.stage]?.description}
        </Typography>
      </Box>
      
      {/* Progress bar with percentage */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Progresso
          </Typography>
          <Typography variant="body2" fontWeight="medium">
            {Math.round(task.progress)}%
          </Typography>
        </Box>
        
        <LinearProgress 
          variant="determinate" 
          value={task.progress} 
          sx={{ height: 8, borderRadius: 4 }}
          aria-valuetext={ariaValueText}
          aria-valuenow={Math.round(task.progress)}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </Box>
      
      {/* Metrics grid - time, quality, iterations */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        {/* Time remaining */}
        <Grid item xs={12} sm={4}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <ScheduleIcon color="action" sx={{ mr: 1 }} />
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Tempo stimato
              </Typography>
              {isProcessing && task.estimatedTimeRemaining ? (
                <Typography variant="body2" fontWeight="medium">
                  {formatTimeRemaining(task.estimatedTimeRemaining)}
                </Typography>
              ) : isProcessing ? (
                <Skeleton width={80} height={24} />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  --
                </Typography>
              )}
            </Box>
          </Box>
        </Grid>
        
        {/* Quality score */}
        <Grid item xs={12} sm={4}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <QualityIcon color="action" sx={{ mr: 1 }} />
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Qualità
              </Typography>
              {task.quality ? (
                <Tooltip title={`Score di qualità: ${task.quality}/100`}>
                  <Typography variant="body2" fontWeight="medium">
                    {Math.round(task.quality)}%
                  </Typography>
                </Tooltip>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  --
                </Typography>
              )}
            </Box>
          </Box>
        </Grid>
        
        {/* Iterations */}
        <Grid item xs={12} sm={4}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <IterationsIcon color="action" sx={{ mr: 1 }} />
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">
                Iterazioni
              </Typography>
              {task.iterations ? (
                <Typography variant="body2" fontWeight="medium">
                  {task.iterations} {task.iterations === 1 ? 'ciclo' : 'cicli'}
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  --
                </Typography>
              )}
            </Box>
          </Box>
        </Grid>
      </Grid>
      
      {/* Process stages stepper */}
      <Stepper 
        activeStep={activeStep} 
        alternativeLabel 
        sx={{ mt: 3 }}
        aria-label="Fasi del processo"
      >
        {orderedStages.map((stage) => (
          <Step key={stage} completed={orderedStages.indexOf(stage) < activeStep}>
            <StepLabel>
              <Typography variant="caption">
                {stageInfo[stage].label}
              </Typography>
            </StepLabel>
          </Step>
        ))}
      </Stepper>
      
      {/* Error message if present */}
      {renderError()}
      
      {/* Processing indicator */}
      {isProcessing && (
        <Box 
          sx={{ 
            display: 'flex', 
            justifyContent: 'center', 
            mt: 2 
          }}
          aria-live="polite"
        >
          <CircularProgress size={20} sx={{ mr: 1 }} />
          <Typography variant="body2" color="text.secondary">
            Elaborazione in corso...
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default TaskProgress; 