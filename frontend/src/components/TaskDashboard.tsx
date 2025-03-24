import React, { useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Stepper,
  Step,
  StepLabel,
  Typography,
  Divider,
  Container,
  Button,
  useTheme
} from '@mui/material';

import { useTask } from '../context/TaskContext';
import FileUploader from './FileUploader';
import ContextualHelp from './ContextualHelp';
import VersionControl from './VersionControl';
import SimpleDocxPreviewEditor from './SimpleDocxPreviewEditor';
import DocumentCompare from './DocumentCompare';
import TaskProgress from './TaskProgress';

// Define the steps based on process stages
const steps = [
  { label: 'Caricamento', stage: 'upload' },
  { label: 'Estrazione', stage: 'extraction' },
  { label: 'Analisi', stage: 'analysis' },
  { label: 'Generazione', stage: 'writer' },
  { label: 'Revisione', stage: 'reviewer' },
  { label: 'Miglioramento', stage: 'refinement' },
  { label: 'Formattazione', stage: 'formatting' },
  { label: 'Finalizzazione', stage: 'finalization' }
];

// Get step index from stage
const getStepIndex = (stage: string): number => {
  const index = steps.findIndex(step => step.stage === stage);
  return index >= 0 ? index : 0;
};

const TaskDashboard: React.FC = () => {
  const theme = useTheme();
  const { task } = useTask();
  const [compareMode, setCompareMode] = useState(false);
  const [compareVersions, setCompareVersions] = useState<[string, string] | null>(null);

  // Handle version selection for comparison
  const handleVersionCompare = (versionIds: [string, string]) => {
    setCompareVersions(versionIds);
    setCompareMode(true);
  };
  
  // Handle single version selection
  const handleVersionSelect = (versionId: string) => {
    setCompareMode(false);
  };
  
  // Get the active step from current stage
  const activeStep = getStepIndex(task.stage);
  
  // Render the main content based on current stage
  const renderMainContent = () => {
    if (compareMode && compareVersions) {
      return <DocumentCompare versionIds={compareVersions} />;
    }
    
    switch (task.stage) {
      case 'upload':
        return <FileUploader />;
      
      case 'extraction':
      case 'analysis':
      case 'writer':
      case 'reviewer':
        return (
          <Box sx={{ py: 4, textAlign: 'center' }}>
            <TaskProgress />
            <Typography variant="body1" sx={{ mt: 2 }}>
              {task.message || 'Elaborazione in corso...'}
            </Typography>
          </Box>
        );
      
      case 'refinement':
      case 'formatting':
      case 'finalization':
        return (
          task.currentReportId ? (
            <SimpleDocxPreviewEditor 
              reportId={task.currentReportId} 
              readOnly={task.stage !== 'refinement'}
            />
          ) : (
            <Box sx={{ py: 4, textAlign: 'center' }}>
              <Typography color="error">
                Nessun report disponibile da visualizzare
              </Typography>
            </Box>
          )
        );
      
      default:
        return (
          <Box sx={{ py: 4, textAlign: 'center' }}>
            <Typography variant="h5" gutterBottom>
              Benvenuto nel Generatore di Report Assicurativi
            </Typography>
            <Typography variant="body1">
              Inizia caricando i documenti che desideri elaborare.
            </Typography>
          </Box>
        );
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
      {/* Process stepper */}
      <Paper 
        elevation={2} 
        sx={{ 
          p: 3, 
          mb: 4,
          borderLeft: task.error 
            ? `4px solid ${theme.palette.error.main}` 
            : `4px solid ${theme.palette.primary.main}` 
        }}
      >
        <Typography variant="h5" gutterBottom>
          Generazione Report Assicurativo
        </Typography>
        
        <Stepper activeStep={activeStep} alternativeLabel sx={{ mt: 3 }}>
          {steps.map((step, index) => (
            <Step key={step.stage} completed={index < activeStep}>
              <StepLabel>{step.label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Paper>
      
      <Grid container spacing={3}>
        {/* Main content area */}
        <Grid item xs={12} md={8}>
          <Box sx={{ mb: 3 }}>
            {task.error && (
              <Paper 
                elevation={1} 
                sx={{ 
                  p: 2, 
                  mb: 3, 
                  bgcolor: `${theme.palette.error.light}20`,
                  borderLeft: `4px solid ${theme.palette.error.main}`
                }}
              >
                <Typography variant="subtitle1" color="error" fontWeight="bold" gutterBottom>
                  Si è verificato un errore
                </Typography>
                <Typography variant="body2">
                  {task.error}
                </Typography>
              </Paper>
            )}
            
            {renderMainContent()}
          </Box>
        </Grid>
        
        {/* Sidebar for context and controls */}
        <Grid item xs={12} md={4}>
          {/* Contextual help */}
          <ContextualHelp />
          
          {/* Version control if a report exists */}
          {task.currentReportId && task.versions && task.versions.length > 0 && (
            <VersionControl 
              onVersionSelect={handleVersionSelect} 
              onCompareSelect={handleVersionCompare}
            />
          )}
          
          {/* Task statistics if task is active */}
          {task.status === 'in_progress' && (
            <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Statistiche del Task
              </Typography>
              <Divider sx={{ mb: 1 }} />
              <Grid container spacing={1}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    ID Task:
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    {task.id.substring(0, 8)}
                  </Typography>
                </Grid>
                
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Avviato:
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    {task.startTime ? new Date(task.startTime).toLocaleTimeString() : 'N/A'}
                  </Typography>
                </Grid>
                
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Progresso:
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    {task.progress}%
                  </Typography>
                </Grid>
                
                {task.estimatedTimeRemaining !== undefined && (
                  <>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        Tempo rimasto:
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        {Math.round(task.estimatedTimeRemaining / 60)} min
                      </Typography>
                    </Grid>
                  </>
                )}
              </Grid>
            </Paper>
          )}
          
          {/* Action buttons based on stage */}
          <Paper elevation={1} sx={{ p: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Azioni Disponibili
            </Typography>
            <Divider sx={{ mb: 2 }} />
            
            {task.stage === 'finalization' && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Button 
                  variant="contained" 
                  color="primary" 
                  fullWidth
                  onClick={() => {}}
                >
                  Scarica Report (DOCX)
                </Button>
                <Button 
                  variant="outlined" 
                  color="primary" 
                  fullWidth
                  onClick={() => {}}
                >
                  Scarica Report (PDF)
                </Button>
                <Button 
                  variant="outlined" 
                  color="secondary" 
                  fullWidth
                  onClick={() => {}}
                >
                  Inizia Nuovo Report
                </Button>
              </Box>
            )}
            
            {task.stage === 'idle' && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Button 
                  variant="contained" 
                  color="primary" 
                  fullWidth
                  onClick={() => {}}
                >
                  Inizia Nuovo Report
                </Button>
              </Box>
            )}
            
            {compareMode && (
              <Box sx={{ mt: 1 }}>
                <Button 
                  variant="outlined" 
                  color="primary" 
                  fullWidth
                  onClick={() => setCompareMode(false)}
                >
                  Torna al Report
                </Button>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default TaskDashboard; 