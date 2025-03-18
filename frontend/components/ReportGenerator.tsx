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
import { generateReport } from '../api/generate'; // Import the API function

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

// Define interfaces for the types
interface ReportGeneratorProps {
  reportId: number | null;
  onGenerateSuccess: (text: string) => void;
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

const ReportGenerator: React.FC<ReportGeneratorProps> = ({ 
  reportId, 
  onGenerateSuccess 
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
    
    if (loading) {
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
  }, [loading, currentStep]);

  // Simulate progress between API progress updates
  useEffect(() => {
    let progressInterval: NodeJS.Timeout;
    
    if (loading) {
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
  }, [loading, currentStep]);

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
      setError('No document has been uploaded');
      return;
    }

    // Reset states
    setLoading(true);
    setError(null);
    setCurrentStep(0);
    setDisplayStep(0);
    setProgress(5); // Start with a small progress indicator immediately
    setDisplayProgress(5);
    setProcessingTime(0);
    setShowLongProcessingMessage(false);
    setStepTransition(false);

    // Add a small artificial delay with increasing progress to provide immediate feedback
    setTimeout(() => setProgress(10), 300);
    setTimeout(() => setProgress(20), 600);

    try {
      // Use the API function with progress callback
      const result = await generateReport(
        reportId, 
        {}, // No special options
        (progressUpdate: ProgressUpdate) => {
          // Update UI based on API progress
          if (progressUpdate.step !== undefined) {
            setCurrentStep(progressUpdate.step);
          }
          
          if (progressUpdate.progress !== undefined) {
            setProgress(progressUpdate.progress);
          }
          
          // After the initial step, move to step 1 after 2 seconds
          // and step 2 after 4 more seconds to simulate progress
          if (progressUpdate.step === 0) {
            setTimeout(() => {
              if (loading) { // Check if still loading
                setCurrentStep(1);
                setTimeout(() => {
                  if (loading) { // Check if still loading
                    setCurrentStep(2);
                  }
                }, 4000);
              }
            }, 2000);
          }
        }
      ) as ReportResponse;

      if (result.error) {
        throw new Error(result.content || 'Failed to generate report');
      }

      // Small delay to show the completion step before moving on
      setTimeout(() => {
        onGenerateSuccess(result.content || '');
        setLoading(false);
      }, 1000);
    } catch (err) {
      console.error('Error generating report:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate report. Please try again.');
      setLoading(false);
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
        {!loading && (
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
        disabled={loading || !reportId}
        startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <AutoAwesomeIcon />}
        fullWidth
        sx={{ 
          mb: 2,
          position: 'relative',
          '&:disabled': {
            bgcolor: loading ? 'secondary.main' : 'action.disabledBackground',
            color: loading ? 'secondary.contrastText' : 'action.disabled',
            opacity: loading ? 0.8 : 0.7
          },
          transition: 'all 0.3s ease',
          overflow: 'hidden',
          ...(loading && {
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
        {loading ? 'Generating Report...' : 'Generate AI Report'}
        {loading && (
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
      
      {loading && (
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
      
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Paper>
  );
};

export default ReportGenerator; 