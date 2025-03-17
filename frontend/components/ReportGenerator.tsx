import React, { useState, useEffect } from 'react';
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
  LinearProgress
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { generateReport } from '../api/generate'; // Import the API function

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
  { label: "Extracting content 📄", value: 30 },
  { label: "Understanding document structure 📊", value: 60 },
  { label: "Generating report with AI 🤖", value: 90 },
  { label: "Done! Reviewing your report... ✅", value: 100 }
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

  const handleGenerateReport = async () => {
    if (!reportId) {
      setError('No document has been uploaded');
      return;
    }

    // Reset states
    setLoading(true);
    setError(null);
    setCurrentStep(0);
    setProgress(0);
    setProcessingTime(0);
    setShowLongProcessingMessage(false);

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
        startIcon={!loading && <AutoAwesomeIcon />}
        fullWidth
        sx={{ mb: 2 }}
      >
        {loading ? 'Processing...' : 'Generate AI Report'}
      </Button>
      
      {loading && (
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Typography variant="body2" sx={{ flexGrow: 1 }}>
              {PROCESSING_STEPS[currentStep].label}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {progress}%
            </Typography>
          </Box>
          
          <LinearProgress 
            variant="determinate" 
            value={progress} 
            sx={{ height: 8, borderRadius: 4, mb: 2 }} 
          />
          
          <Typography variant="body2" color="text.secondary" align="center">
            {processingTime < 20 ? (
              `Processing time: ${processingTime} seconds (typically takes 10-15 seconds)`
            ) : showLongProcessingMessage ? (
              "Still working on it... AI is carefully reviewing your documents."
            ) : (
              `Processing time: ${processingTime} seconds`
            )}
          </Typography>
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