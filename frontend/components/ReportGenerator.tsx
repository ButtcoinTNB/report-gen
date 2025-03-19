import React, { useState, useEffect, useRef } from 'react';
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
  Fade
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import DescriptionIcon from '@mui/icons-material/Description';
import SchemaIcon from '@mui/icons-material/Schema';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { generateReport } from '../src/services/api'; // Import the API function
import { Report } from '../src/types';

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
    onGenerate: (report: Report) => void;
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

const ReportGenerator: React.FC<Props> = ({ reportId, onGenerate, onError }) => {
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
  const actualProgressRef = useRef(0);

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

  const handleGenerateReport = async () => {
    if (!reportId) {
        onError(new Error('No document has been uploaded'));
        return;
    }

    // Reset states
    setState(prev => ({ ...prev, isGenerating: true, error: null, documentIds: [], additionalInfo: '', templateId: undefined }));
    setCurrentStep(0);
    setDisplayStep(0);
    setProgress(0);

    try {
        const result: ReportResponse = await generateReport(
            {
                reportId,
                documentIds: state.documentIds,
                additionalInfo: state.additionalInfo,
                templateId: state.templateId
            },
            {},
            (update: ProgressUpdate) => {
                if (update.step !== undefined) {
                    setCurrentStep(update.step);
                }
                if (update.progress !== undefined) {
                    setProgress(update.progress);
                }
            }
        );

        // Small delay to show the completion step before moving on
        setTimeout(() => {
            onGenerate({
                report_id: reportId,
                content: result.content,
                title: 'Generated Report',
                file_path: '',
                is_finalized: false,
                files_cleaned: false,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            });
            setState(prev => ({ ...prev, isGenerating: false }));
        }, 1000);
    } catch (err) {
        console.error('Error generating report:', err);
        const error = err instanceof Error ? err : new Error('Failed to generate report. Please try again.');
        onError(error);
        setState(prev => ({ ...prev, isGenerating: false, error }));
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h5" gutterBottom>
        AI Report Generation
      </Typography>
      
      <Divider sx={{ my: 2 }} />
      
      <Box sx={{ mb: 2 }}>
        <Typography variant="body1" paragraph>
          Click the button below to analyze your uploaded documents and generate a 
          professional insurance report using AI.
        </Typography>
        {!state.isGenerating && (
          <Typography variant="body2" color="text.secondary">
            Processing typically takes 10-15 seconds.
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
        {state.isGenerating ? 'Generating Report...' : 'Generate AI Report'}
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
                  `Processing time: ${processingTime} seconds (typically takes 10-15 seconds)`
                ) : showLongProcessingMessage ? (
                  <Fade in={true}>
                    <Box sx={{ fontWeight: 'medium', color: 'warning.main' }}>
                      Still working on it... AI is carefully reviewing your documents.
                    </Box>
                  </Fade>
                ) : (
                  `Processing time: ${processingTime} seconds`
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
  );
};

export default ReportGenerator; 