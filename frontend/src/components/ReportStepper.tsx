import React, { useState, useEffect } from 'react';
import { 
  Stepper, 
  Step, 
  StepLabel, 
  Box, 
  Button, 
  Paper, 
  Typography, 
  Divider, 
  CircularProgress,
  Zoom,
  Fade,
  Collapse
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import FileUploader from './FileUploader';
import ReportGenerator from './ReportGenerator';
import { DocxPreviewEditor } from './DocxPreviewEditor';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { setActiveStep, resetState } from '../store/reportSlice';
import JourneyVisualizer from './JourneyVisualizer';
import UploadProgressTracker from './UploadProgressTracker';

interface Props {
  reportId?: string;
  onGenerate?: (reportData: any) => void;
  onError?: (error: Error) => void;
}

const getStepContent = (
  step: number, 
  reportId: string | null, 
  onReportGenerated: (reportData: any) => void, 
  onGenerateError: (error: Error) => void
) => {
  switch (step) {
    case 0:
      return <FileUploader reportId={reportId || ''} allowContinueWhileUploading={true} />;
    case 1:
      return <ReportGenerator reportId={reportId || ''} onGenerate={onReportGenerated} onError={onGenerateError} />;
    case 2:
      return <DocxPreviewEditor 
        initialContent={''}
        downloadUrl={''}
        reportId={reportId || ''}
        showRefinementOptions={true}
      />;
    default:
      return <Typography>Passo sconosciuto</Typography>;
  }
};

const ReportStepper: React.FC<Props> = ({ reportId: propReportId, onGenerate, onError }) => {
  const dispatch = useAppDispatch();
  const { activeStep, reportId: storeReportId, documentIds, backgroundUpload, additionalInfo } = useAppSelector(state => state.report);
  const [generatedReport, setGeneratedReport] = useState<any>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [readyForAutoTransition, setReadyForAutoTransition] = useState(false);
  const [showBackgroundUploadStatus, setShowBackgroundUploadStatus] = useState(false);
  
  // Define steps
  const steps = [
    { label: 'Carica Documenti', id: 'upload' },
    { label: 'Genera Report', id: 'generate' },
    { label: 'Refina & Modifica', id: 'refine' },
  ];

  // Combined report ID from props or store
  const reportId = propReportId || storeReportId;

  // Check if auto-transition should trigger (when upload completes and we have sufficient info)
  useEffect(() => {
    if (
      activeStep === 0 && 
      backgroundUpload && 
      !backgroundUpload.isUploading && 
      backgroundUpload.progress === 100 && 
      additionalInfo.trim().length > 10
    ) {
      setReadyForAutoTransition(true);
      
      // Auto-transition after a short delay
      const timer = setTimeout(() => {
        if (readyForAutoTransition) {
          handleNext();
        }
      }, 2000);
      
      return () => clearTimeout(timer);
    }
  }, [backgroundUpload, additionalInfo, activeStep]);

  // Show background upload status when user moves to next step while uploads are in progress
  useEffect(() => {
    if (activeStep > 0 && backgroundUpload?.isUploading) {
      setShowBackgroundUploadStatus(true);
    } else if (!backgroundUpload?.isUploading) {
      // Hide after a short delay when uploads complete
      const timer = setTimeout(() => {
        setShowBackgroundUploadStatus(false);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [activeStep, backgroundUpload?.isUploading]);

  // Handle completion of steps
  useEffect(() => {
    const newCompletedSteps = [...completedSteps];
    
    if (activeStep > 0 && !newCompletedSteps.includes('upload')) {
      newCompletedSteps.push('upload');
    }
    
    if (generatedReport && !newCompletedSteps.includes('generate')) {
      newCompletedSteps.push('generate');
    }
    
    if (newCompletedSteps.length !== completedSteps.length) {
      setCompletedSteps(newCompletedSteps);
    }
  }, [activeStep, generatedReport]);

  // Reset component state when stepper is reset
  useEffect(() => {
    if (activeStep === 0) {
      setGeneratedReport(null);
      setError(null);
    }
  }, [activeStep]);

  const handleNext = () => {
    setIsTransitioning(true);
    
    setTimeout(() => {
      dispatch(setActiveStep(activeStep + 1));
      setIsTransitioning(false);
      setReadyForAutoTransition(false);
    }, 300);
  };

  const handleBack = () => {
    setIsTransitioning(true);
    
    setTimeout(() => {
      dispatch(setActiveStep(activeStep - 1));
      setIsTransitioning(false);
    }, 300);
  };

  const handleReset = () => {
    dispatch(resetState());
  };

  const handleReportGenerated = (reportData: any) => {
    setGeneratedReport(reportData);
    if (onGenerate) {
      onGenerate(reportData);
    }
    // Auto-advance to next step
    handleNext();
  };

  const handleGenerateError = (err: Error) => {
    setError(err);
    if (onError) {
      onError(err);
    }
  };

  // Determine if the Next button should be disabled
  const isNextDisabled = () => {
    switch (activeStep) {
      case 0:
        // Files will be uploaded in background, but we need at least one file uploading or uploaded
        return !backgroundUpload || (!backgroundUpload.isUploading && backgroundUpload.uploadedFiles === 0);
      case 1:
        // Disable if report is not yet generated
        return !generatedReport;
      case 2:
        // Always enable in refinement step
        return false;
      default:
        return false;
    }
  };

  // Determine what the Next button should say
  const getNextButtonText = () => {
    switch (activeStep) {
      case 0:
        return 'Continua';
      case 1:
        return generatedReport ? 'Visualizza Report' : 'Genera Report';
      case 2:
        return 'Finalizza';
      default:
        return 'Avanti';
    }
  };

  const getCurrentJourneyStep = () => {
    switch (activeStep) {
      case 0: return backgroundUpload?.isUploading ? 0 : 1;
      case 1: return 2;
      case 2: return 3;
      default: return 0;
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Background upload status (shown when user moves to subsequent steps) */}
      <Collapse in={showBackgroundUploadStatus && activeStep > 0}>
        <Box sx={{ position: 'fixed', bottom: 16, right: 16, zIndex: 1200, width: 320 }}>
          <UploadProgressTracker variant="compact" />
        </Box>
      </Collapse>
      
      <Paper elevation={0} sx={{ 
        mb: 4, 
        bgcolor: 'background.default',
        position: 'sticky',
        top: 0,
        zIndex: 10,
        pt: 2,
        pb: 1,
        borderBottom: '1px solid',
        borderColor: 'divider'
      }}>
        <Box sx={{ mb: 2 }}>
          <JourneyVisualizer 
            activeStep={getCurrentJourneyStep()}
            stepsCompleted={completedSteps}
            showContent={false}
          />
        </Box>
        
        <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 1 }}>
          {steps.map((step, index) => (
            <Step key={index}>
              <StepLabel>{step.label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Paper>
      
      <Box sx={{ position: 'relative', minHeight: '400px' }}>
        <Fade in={!isTransitioning} timeout={300}>
          <Box>
            {activeStep === steps.length ? (
              <Box sx={{ mt: 2 }}>
                <Typography>Tutti i passaggi sono stati completati</Typography>
                <Button onClick={handleReset} sx={{ mt: 2 }}>
                  Inizia di Nuovo
                </Button>
              </Box>
            ) : (
              <Box sx={{ mt: 2 }}>
                {getStepContent(activeStep, reportId, handleReportGenerated, handleGenerateError)}
                
                {readyForAutoTransition && activeStep === 0 && (
                  <Zoom in={readyForAutoTransition}>
                    <Paper 
                      elevation={4} 
                      sx={{ 
                        mt: 2, 
                        p: 2, 
                        display: 'flex',
                        alignItems: 'center',
                        bgcolor: 'success.light',
                        color: 'success.contrastText',
                        borderRadius: 2
                      }}
                    >
                      <AutoAwesomeIcon sx={{ mr: 1 }} />
                      <Typography>
                        Upload completato! Proseguendo alla generazione del report...
                      </Typography>
                    </Paper>
                  </Zoom>
                )}
                
                <Box sx={{ mt: 4, display: 'flex', justifyContent: 'space-between' }}>
                  <Button
                    variant="outlined"
                    disabled={activeStep === 0}
                    onClick={handleBack}
                    startIcon={<NavigateBeforeIcon />}
                  >
                    Indietro
                  </Button>
                  
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleNext}
                    disabled={isNextDisabled()}
                    endIcon={<NavigateNextIcon />}
                  >
                    {getNextButtonText()}
                  </Button>
                </Box>
              </Box>
            )}
          </Box>
        </Fade>
      </Box>
    </Box>
  );
};

export default ReportStepper; 