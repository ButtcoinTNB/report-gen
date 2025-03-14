import React, { useState } from 'react';
import { 
  Container, 
  Box, 
  Typography, 
  Paper, 
  Button, 
  Stepper, 
  Step, 
  StepLabel,
  TextField,
  CircularProgress
} from '@mui/material';
import Navbar from '../components/Navbar';
import FileUpload from '../components/FileUpload';
import { generateReport } from '../api/generate.js';
import { finalizeReport, downloadReport } from '../api/report';

export default function Home() {
  const [activeStep, setActiveStep] = useState(0);
  const [reportId, setReportId] = useState(null);
  const [generatedText, setGeneratedText] = useState('');
  const [editedText, setEditedText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);
  
  // Simplified steps
  const steps = ['Upload Documents', 'Edit Report', 'Download PDF'];

  // Handler for upload success - immediately generate report
  const handleUploadSuccess = async (id) => {
    console.log('Upload success with report ID:', id);
    setReportId(id);
    setIsGenerating(true);
    
    try {
      // Auto-generate report
      console.log('Calling generateReport with ID:', id);
      const result = await generateReport(id);
      console.log('Report generation result:', result);
      
      if (result && result.content) {
        console.log('Setting report content:', result.content.substring(0, 100) + '...');
        setGeneratedText(result.content);
        setEditedText(result.content);
        setActiveStep(1); // Move to edit step automatically
      } else {
        console.error('Missing content in result:', result);
        throw new Error('Failed to generate report content');
      }
    } catch (error) {
      console.error('Error generating report:', error);
      alert('There was an error generating your report. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  // Handler for finalizing and downloading the report
  const handleDownloadReport = async () => {
    if (!reportId) {
      alert('No report ID found. Please upload documents and generate a report first.');
      return;
    }
    
    setIsDownloading(true);
    try {
      // First finalize the report with edited text
      console.log('Finalizing report with ID:', reportId);
      const finalizeResult = await finalizeReport({
        report_id: reportId,
        content: editedText,
        template_id: 1  // Always use template ID 1
      });
      
      console.log('Finalize result:', finalizeResult);
      
      if (!finalizeResult || !finalizeResult.success) {
        throw new Error('Report finalization failed');
      }
      
      // Short delay to ensure the file is saved
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Then download it
      console.log('Downloading report with ID:', reportId);
      const result = await downloadReport(reportId);
      
      console.log('Download result:', result);
      
      if (result && result.data && result.data.download_url) {
        // Open the download URL in a new tab or trigger download
        const downloadUrl = result.data.download_url;
        console.log('Opening download URL:', downloadUrl);
        
        // Store download URL
        setDownloadUrl(downloadUrl);
        
        // Open in new tab
        window.open(downloadUrl, '_blank');
        
        // Move to final step
        setActiveStep(2);
      } else {
        throw new Error('Failed to get download URL');
      }
    } catch (error) {
      console.error('Error in report finalization/download process:', error);
      
      let errorMessage = 'There was an error downloading your report. Please try again.';
      if (error.message) {
        errorMessage += ' Error details: ' + error.message;
      }
      
      alert(errorMessage);
    } finally {
      setIsDownloading(false);
    }
  };

  // Render different components based on the active step
  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        // Upload step
        return (
          <>
            <Typography variant="h5" gutterBottom align="center" sx={{ mb: 3 }}>
              Upload your case documents
            </Typography>
            <Typography paragraph align="center" sx={{ mb: 4 }}>
              Please upload all relevant files for your insurance case. Our AI will analyze them and generate a properly formatted report.
            </Typography>
            <FileUpload onUploadSuccess={handleUploadSuccess} />
            {isGenerating && (
              <Box sx={{ textAlign: 'center', mt: 4 }}>
                <CircularProgress />
                <Typography variant="body1" sx={{ mt: 2 }}>
                  Analyzing your documents and generating report...
                </Typography>
              </Box>
            )}
          </>
        );
      case 1:
        // Edit report step
        return (
          <>
            <Typography variant="h5" gutterBottom align="center" sx={{ mb: 3 }}>
              Review and Edit Report
            </Typography>
            <Typography paragraph align="center" sx={{ mb: 4 }}>
              This is the AI-generated report based on your documents. You can edit it before downloading.
            </Typography>
            <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
              <TextField
                fullWidth
                multiline
                minRows={15}
                maxRows={30}
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                variant="outlined"
                sx={{ mb: 3, fontFamily: 'Georgia, serif' }}
              />
              <Button
                variant="contained"
                color="primary"
                size="large"
                onClick={handleDownloadReport}
                disabled={isDownloading || !editedText.trim()}
                fullWidth
                startIcon={isDownloading ? <CircularProgress size={20} color="inherit" /> : null}
              >
                {isDownloading ? 'Processing...' : 'Download PDF Report'}
              </Button>
            </Paper>
          </>
        );
      case 2:
        // Download complete step
        return (
          <>
            <Typography variant="h5" gutterBottom align="center" sx={{ mb: 3 }}>
              Your Report is Ready
            </Typography>
            <Paper elevation={3} sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="h6" gutterBottom>
                Success! Your report has been formatted and is ready.
              </Typography>
              <Typography paragraph sx={{ mb: 4 }}>
                Your PDF maintains the same formatting and style as our standard templates, with your specific case information.
              </Typography>
              {downloadUrl && (
                <Button 
                  variant="contained" 
                  color="primary"
                  href={downloadUrl}
                  target="_blank"
                  sx={{ mt: 2 }}
                >
                  Download Again
                </Button>
              )}
              <Button 
                variant="outlined"
                onClick={() => {
                  setActiveStep(0);
                  setReportId(null);
                  setGeneratedText('');
                  setEditedText('');
                  setDownloadUrl(null);
                }}
                sx={{ mt: 2, ml: 2 }}
              >
                Create New Report
              </Button>
            </Paper>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <>
      <Navbar />
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h4" gutterBottom align="center" sx={{ mb: 4 }}>
          Insurance Report Generator
        </Typography>

        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {renderStepContent()}
      </Container>
    </>
  );
} 