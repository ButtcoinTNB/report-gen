import React from 'react';
import { Box, Stepper, Step, StepLabel, Typography, Button, Paper } from '@mui/material';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { setActiveStep } from '../store/reportSlice';
import FileUploader from './FileUploader';
import ReportGenerator from './ReportGenerator';
import ReportEditor from './ReportEditor';
import ReportDownloader from './ReportDownloader';

// Define steps
const steps = [
  'Upload Documents',
  'Generate Report',
  'Review & Edit',
  'Download Report'
];

// Step content components
const getStepContent = (step: number) => {
  switch (step) {
    case 0:
      return <FileUploader />;
    case 1:
      return <ReportGenerator />;
    case 2:
      return <ReportEditor />;
    case 3:
      return <ReportDownloader />;
    default:
      return 'Unknown step';
  }
};

const ReportStepper: React.FC = () => {
  const dispatch = useAppDispatch();
  const activeStep = useAppSelector(state => state.report.activeStep);
  const documentIds = useAppSelector(state => state.report.documentIds);
  const reportId = useAppSelector(state => state.report.reportId);
  const content = useAppSelector(state => state.report.content);
  
  // Handle next step button click
  const handleNext = () => {
    dispatch(setActiveStep(activeStep + 1));
  };
  
  // Handle back button click
  const handleBack = () => {
    dispatch(setActiveStep(activeStep - 1));
  };
  
  // Reset to first step
  const handleReset = () => {
    dispatch(setActiveStep(0));
  };
  
  // Determine if the next button should be disabled
  const isNextDisabled = (): boolean => {
    switch (activeStep) {
      case 0:
        return documentIds.length === 0; // Disable if no documents uploaded
      case 1:
        return !reportId; // Disable if no report generated
      case 2:
        return !content; // Disable if no content to edit
      default:
        return false;
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Stepper activeStep={activeStep} sx={{ pt: 3, pb: 5 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      
      <div>
        {activeStep === steps.length ? (
          <Paper square elevation={0} sx={{ p: 3, bgcolor: 'background.default' }}>
            <Typography>All steps completed - Report is ready!</Typography>
            <Button onClick={handleReset} sx={{ mt: 1, mr: 1 }}>
              Start New Report
            </Button>
          </Paper>
        ) : (
          <div>
            {getStepContent(activeStep)}
            
            <Box sx={{ display: 'flex', flexDirection: 'row', pt: 2 }}>
              <Button
                color="inherit"
                disabled={activeStep === 0}
                onClick={handleBack}
                sx={{ mr: 1 }}
              >
                Back
              </Button>
              <Box sx={{ flex: '1 1 auto' }} />
              
              {activeStep < steps.length - 1 ? (
                <Button 
                  onClick={handleNext}
                  disabled={isNextDisabled()}
                  variant="contained"
                >
                  Next
                </Button>
              ) : (
                <Button onClick={handleNext} variant="contained">
                  Finish
                </Button>
              )}
            </Box>
          </div>
        )}
      </div>
    </Box>
  );
};

export default ReportStepper; 