import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Paper,
  CircularProgress, 
  Alert,
  Divider,
  Stepper,
  Step,
  StepLabel,
  LinearProgress,
  keyframes,
  Fade,
  TextField,
  Collapse,
  Zoom,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import DescriptionIcon from '@mui/icons-material/Description';
import SchemaIcon from '@mui/icons-material/Schema';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CloudDoneIcon from '@mui/icons-material/CloudDone';
import { generateApi } from '../services'; // Import the API adapter
import { Report, ReportCamel, adaptReport } from '../types';
import { logger } from '../utils/logger';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { setAdditionalInfo, setBackgroundUpload, setReportId } from '../store/reportSlice';
import JourneyVisualizer from './JourneyVisualizer';
import { generateUUID } from '../utils/common';

// Define a subtle pulsing animation for the progress bar
const pulse = keyframes`
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
  100% {
    opacity: 1;
  }
`;

// Define a shimmer animation for the loading button
const shimmer = keyframes`
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
`;

interface Props {
    reportId: string | null;  // UUID
    onGenerate: (report: ReportCamel) => void;
    onError: (error: Error) => void;
}

interface State {
    isGenerating: boolean;
    error: Error | null;  // Changed from string to Error
    documentIds: string[];  // UUIDs
    additionalInfo: string;
    templateId?: string;  // UUID
}

interface ProgressUpdate {
    step: number;
    message: string;
    progress: number;
}

interface ReportResponse {
    content: string;
    error?: boolean;
}

// Define the processing steps
const PROCESSING_STEPS = [
  { label: "Extracting content 📄", value: 30, icon: <DescriptionIcon /> },
  { label: "Understanding document structure 📊", value: 60, icon: <SchemaIcon /> },
  { label: "Generating report with AI 🤖", value: 90, icon: <SmartToyIcon /> },
  { label: "Done! Reviewing your report... ✅", value: 100, icon: <CheckCircleIcon /> }
];

const AdditionalInfoInput: React.FC = () => {
  const dispatch = useAppDispatch();
  const additionalInfo = useAppSelector(state => state.report.additionalInfo);
  const backgroundUpload = useAppSelector(state => state.report.backgroundUpload);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleInfoChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setAdditionalInfo(event.target.value));
  };

  const handleSaveInfo = () => {
    setIsSaving(true);
    
    // Simulate a brief save operation
    setTimeout(() => {
      // Update the last activity time in the store
      dispatch(setAdditionalInfo(additionalInfo));
      setIsSaving(false);
      
      // Show success message briefly
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    }, 400);
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Informazioni Aggiuntive
      </Typography>
      
      <Typography variant="body2" color="text.secondary" paragraph>
        {backgroundUpload?.isUploading 
          ? "Mentre i tuoi file vengono caricati, fornisci ulteriori informazioni che aiuteranno a generare un report più accurato."
          : "Fornisci ulteriori informazioni che aiuteranno a generare un report più accurato."}
      </Typography>
      
      <TextField
        fullWidth
        multiline
        rows={4}
        placeholder="Inserisci dettagli come contesto del sinistro, requisiti speciali o aspetti specifici su cui concentrarsi..."
        value={additionalInfo}
        onChange={handleInfoChange}
        sx={{ mb: 2 }}
        helperText={`${additionalInfo.length}/1000 caratteri - Sii specifico per ottenere risultati migliori`}
      />
      
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
        {saveSuccess && (
          <Typography 
            variant="body2" 
            color="success.main" 
            sx={{ mr: 2, display: 'flex', alignItems: 'center' }}
          >
            <CheckCircleIcon fontSize="small" sx={{ mr: 0.5 }} />
            Informazioni salvate!
          </Typography>
        )}
        <Button 
          variant="contained" 
          color="primary"
          onClick={handleSaveInfo}
          disabled={isSaving}
          startIcon={isSaving ? <CircularProgress size={20} color="inherit" /> : null}
        >
          {isSaving ? 'Salvataggio...' : 'Salva Informazioni'}
        </Button>
      </Box>
      
      {backgroundUpload?.isUploading && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            I tuoi file vengono caricati in background ({backgroundUpload.uploadedFiles || 0}/{backgroundUpload.totalFiles || 0})
          </Typography>
          <Box sx={{ mt: 1, width: '100%', height: 4, bgcolor: 'grey.200', borderRadius: 1, overflow: 'hidden' }}>
            <Box 
              sx={{ 
                width: `${backgroundUpload.progress}%`, 
                height: '100%', 
                bgcolor: 'primary.main',
                transition: 'width 0.3s ease-in-out'
              }} 
            />
          </Box>
        </Alert>
      )}
    </Paper>
  );
};

const ReportGenerator: React.FC<Props> = ({ reportId: propReportId, onGenerate, onError }) => {
  const dispatch = useAppDispatch();
  const backgroundUpload = useAppSelector(state => state.report.backgroundUpload);
  const additionalInfo = useAppSelector(state => state.report.additionalInfo);
  const storeReportId = useAppSelector(state => state.report.reportId);
  
  // Use propReportId if provided, otherwise use from store
  const reportId = propReportId || storeReportId;
  
  const [state, setState] = useState<State>({
    isGenerating: false,
    error: null,
    documentIds: [],
    additionalInfo: '',
  });
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [processingTime, setProcessingTime] = useState(0);
  const [showLongProcessingMessage, setShowLongProcessingMessage] = useState(false);
  const [displayProgress, setDisplayProgress] = useState(0);
  const [displayStep, setDisplayStep] = useState(0);
  const [stepTransition, setStepTransition] = useState(false);
  const [showUploadSuccess, setShowUploadSuccess] = useState(false);
  const actualProgressRef = useRef(0);

  // Function to check if we can autogenerate report
  const canAutoGenerateReport = useCallback(() => {
    return propReportId && 
           !backgroundUpload?.isUploading && 
           backgroundUpload?.progress === 100 && 
           additionalInfo.trim().length > 10;
  }, [propReportId, backgroundUpload, additionalInfo]);

  // Effect to auto-trigger generation when conditions are met
  useEffect(() => {
    // If upload just completed and we have reportId and additionalInfo, autogenerate after a short delay
    if (canAutoGenerateReport() && !state.isGenerating && !showUploadSuccess) {
      setShowUploadSuccess(true);
      
      // Show success message for 3 seconds, then auto-generate
      const timer = setTimeout(() => {
        if (!state.isGenerating) {
          handleGenerateReport();
        }
      }, 3000);
      
      return () => clearTimeout(timer);
    }
  }, [backgroundUpload, propReportId, additionalInfo, state.isGenerating]);

  // Effect to show success message when upload completes
  useEffect(() => {
    if (backgroundUpload?.isUploading === false && backgroundUpload?.progress === 100 && !showUploadSuccess) {
      setShowUploadSuccess(true);
      
      // Auto-hide success message after 5 seconds
      const timer = setTimeout(() => {
        setShowUploadSuccess(false);
      }, 5000);
      
      return () => clearTimeout(timer);
    }
  }, [backgroundUpload]);

  // Clean up uploads when component unmounts
  useEffect(() => {
    return () => {
      if (propReportId) {
        // Notify cleanup service when component unmounts
        dispatch(setBackgroundUpload({
          shouldCleanup: true,
          cleanupReportId: propReportId
        }));
      }
    };
  }, [propReportId, dispatch]);

  // Effect to handle processing time and long processing message
  useEffect(() => {
    let timeInterval: NodeJS.Timeout;
    
    if (state.isGenerating) {
      // Start the processing time counter
      let seconds = 0;
      timeInterval = setInterval(() => {
        seconds += 1;
        setProcessingTime(seconds);
        
        // Show "still working on it" message after 20 seconds
        if (seconds >= 20 && currentStep < PROCESSING_STEPS.length - 1) {
          setShowLongProcessingMessage(true);
        }
      }, 1000);
      
      return () => {
        clearInterval(timeInterval);
      };
    }
  }, [state.isGenerating, currentStep]);

  // Simulate progress between API progress updates
  useEffect(() => {
    let progressInterval: NodeJS.Timeout;
    
    if (state.isGenerating) {
      // Update progress bar smoothly between steps
      progressInterval = setInterval(() => {
        setProgress(prevProgress => {
          const targetProgress = PROCESSING_STEPS[currentStep].value;
          // Move towards the target progress gradually
          if (prevProgress < targetProgress) {
            return Math.min(prevProgress + 1, targetProgress);
          }
          return prevProgress;
        });
      }, 200);
      
      return () => {
        clearInterval(progressInterval);
      };
    }
  }, [state.isGenerating, currentStep]);

  // Effect to animate the progress counter smoothly
  useEffect(() => {
    actualProgressRef.current = progress;
    
    const animateProgress = () => {
      setDisplayProgress(prev => {
        if (prev < actualProgressRef.current) {
          return prev + 1;
        }
        return prev;
      });
    };
    
    const progressAnimationInterval = setInterval(animateProgress, 50);
    
    return () => {
      clearInterval(progressAnimationInterval);
    };
  }, [progress]);

  // Effect to handle step transitions with animation
  useEffect(() => {
    if (currentStep !== displayStep) {
      setStepTransition(true);
      const timer = setTimeout(() => {
        setDisplayStep(currentStep);
        setStepTransition(false);
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [currentStep, displayStep]);

  // Ensure we have a reportId for the Generate button to be enabled
  useEffect(() => {
    if (!reportId) {
      dispatch(setReportId(generateUUID()));
    }
  }, [dispatch, reportId]);

  const handleGenerateReport = async () => {
    try {
      setState(prev => ({ ...prev, isGenerating: true, error: null }));
      setShowUploadSuccess(false);
      
      // Start the progress animation - use setProgress with a number value
      setProgress(10);
      // First step
      setCurrentStep(0);
      
      // Call the generateReport method from the generateApi adapter
      const result = await generateApi.generateReport(
        reportId || '', 
        { text: additionalInfo }
      );
      
      // Success! Create a report object from the result
      const newReport: Report = {
        report_id: result.reportId || reportId || '',
        content: result.message || '', // Use message instead of content
        file_path: '',
        title: 'Report Generated from API',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      
      // Convert to camelCase for frontend use
      const camelReport = adaptReport(newReport);
      
      // Update progress to complete
      setProgress(100);
      setCurrentStep(PROCESSING_STEPS.length - 1);
      
      // Call onGenerate callback with camelCase report
      onGenerate(camelReport);
    } catch (error) {
      logger.error("Error generating report:", error);
      
      // Transform to Error if it's a string
      const errorObj = error instanceof Error ? error : new Error(String(error));
      setState(prev => ({ ...prev, isGenerating: false, error: errorObj }));
      onError(errorObj);
    }
  };

  return (
    <>
      {/* Process Timeline to show overall progress */}
      <JourneyVisualizer 
        activeStep={backgroundUpload?.isUploading ? 0 : (state.isGenerating ? 2 : 1)}
        showContent={true}
        stepsCompleted={backgroundUpload?.isUploading ? [] : ['upload']}
      />
      
      <AdditionalInfoInput />
      
      {/* Upload Success notification */}
      <Collapse in={showUploadSuccess}>
        <Zoom in={showUploadSuccess}>
          <Alert 
            severity="success" 
            icon={<CloudDoneIcon fontSize="inherit" />}
            sx={{ mb: 3 }}
          >
            <Typography variant="subtitle1">
              Upload completato con successo!
            </Typography>
            <Typography variant="body2">
              {canAutoGenerateReport() 
                ? "La generazione del report inizierà automaticamente..." 
                : "Clicca sul pulsante 'Genera Report AI' quando sei pronto."}
            </Typography>
          </Alert>
        </Zoom>
      </Collapse>
      
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          Generazione Report AI
        </Typography>
        
        <Divider sx={{ my: 2 }} />
        
        <Box sx={{ mb: 2 }}>
          <Typography variant="body1" paragraph>
            Clicca il pulsante qui sotto per analizzare i documenti caricati e generare un 
            report assicurativo professionale utilizzando l'AI.
          </Typography>
          {!state.isGenerating && (
            <Typography variant="body2" color="text.secondary">
              L'elaborazione richiede in genere 10-15 secondi.
            </Typography>
          )}
        </Box>
        
        <Button
          variant="contained"
          color="secondary"
          size="large"
          onClick={handleGenerateReport}
          disabled={state.isGenerating || !reportId}
          startIcon={state.isGenerating ? <CircularProgress size={20} color="inherit" /> : <AutoAwesomeIcon />}
          fullWidth
          sx={{ 
            mb: 2,
            position: 'relative',
            '&:disabled': {
              bgcolor: state.isGenerating ? 'secondary.main' : 'action.disabledBackground',
              color: state.isGenerating ? 'secondary.contrastText' : 'action.disabled',
              opacity: state.isGenerating ? 0.8 : 0.7
            },
            transition: 'all 0.3s ease',
            overflow: 'hidden',
            ...(state.isGenerating && {
              '&::before': {
                content: '""',
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
                backgroundSize: '200% 100%',
                animation: `${shimmer} 2s infinite`,
                zIndex: 0
              }
            })
          }}
        >
          {state.isGenerating ? 'Generazione Report...' : 'Genera Report AI'}
          {state.isGenerating && (
            <Box 
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'rgba(0,0,0,0.05)',
                borderRadius: 'inherit'
              }}
            />
          )}
        </Button>
        
        {state.isGenerating && (
          <Box sx={{ mt: 3 }}>
            <Stepper activeStep={displayStep} alternativeLabel sx={{ mb: 3 }}>
              {PROCESSING_STEPS.map((step, index) => (
                <Step key={index} completed={index < displayStep}>
                  <StepLabel StepIconProps={{ 
                    icon: step.icon || index + 1,
                    sx: { 
                      transition: 'transform 0.3s ease, color 0.3s ease',
                      ...(displayStep === index && {
                        transform: 'scale(1.2)',
                        color: 'secondary.main'
                      })
                    }
                  }}>
                    {step.label.split(' ')[0]}
                  </StepLabel>
                </Step>
              ))}
            </Stepper>
            
            <Fade in={!stepTransition} timeout={400}>
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body2" sx={{ 
                    flexGrow: 1, 
                    fontWeight: 'bold',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1
                  }}>
                    <Box component="span" sx={{ 
                      display: 'inline-flex',
                      bgcolor: 'secondary.light',
                      color: 'secondary.contrastText',
                      p: 0.5,
                      borderRadius: 1,
                      fontSize: '1rem'
                    }}>
                      {PROCESSING_STEPS[displayStep].icon}
                    </Box>
                    {PROCESSING_STEPS[displayStep].label}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{
                    minWidth: '36px',
                    textAlign: 'right'
                  }}>
                    {displayProgress}%
                  </Typography>
                </Box>
                
                <LinearProgress 
                  variant="determinate" 
                  value={progress} 
                  sx={{ 
                    height: 8, 
                    borderRadius: 4, 
                    mb: 2,
                    animation: `${pulse} 1.5s ease-in-out infinite`,
                    '& .MuiLinearProgress-bar': {
                      transition: 'transform 0.3s ease'
                    } 
                  }} 
                  color="secondary"
                />
                
                <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                  {processingTime < 20 ? (
                    `Tempo di elaborazione: ${processingTime} secondi (richiede in genere 10-15 secondi)`
                  ) : showLongProcessingMessage ? (
                    <Fade in={true}>
                      <Box sx={{ fontWeight: 'medium', color: 'warning.main' }}>
                        Ancora in elaborazione... L'AI sta analizzando attentamente i tuoi documenti.
                      </Box>
                    </Fade>
                  ) : (
                    `Tempo di elaborazione: ${processingTime} secondi`
                  )}
                </Typography>
              </Box>
            </Fade>
          </Box>
        )}
        
        {state.error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {state.error.message}
          </Alert>
        )}
      </Paper>
    </>
  );
};

export default ReportGenerator;