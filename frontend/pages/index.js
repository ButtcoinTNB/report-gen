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
  CircularProgress,
  Alert,
  Snackbar
} from '@mui/material';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import Navbar from '../components/Navbar';
import FileUpload from '../components/FileUpload';
import { generateReport } from '../api/generate.js';
import { finalizeReport, downloadReport } from '../api/report';

export default function Home() {
  const [activeStep, setActiveStep] = useState(0);
  const [reportId, setReportId] = useState(null);
  const [editedText, setEditedText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [error, setError] = useState(null);
  const [showError, setShowError] = useState(false);
  
  // Simplified steps
  const steps = ['Upload Documents', 'Edit Report', 'Download PDF'];

  // Handler for upload success - immediately generate report
  const handleUploadSuccess = async (id) => {
    console.log('Upload success with report ID:', id);
    setReportId(id);
    setIsGenerating(true);
    setError(null);
    
    try {
      // Auto-generate report
      console.log('Calling generateReport with ID:', id);
      const result = await generateReport(id);
      console.log('Report generation result:', result);
      
      if (result && result.content) {
        console.log('Setting report content:', result.content.substring(0, 100) + '...');
        setEditedText(result.content);
        setActiveStep(1); // Move to edit step automatically
      } else {
        console.error('Missing content in result:', result);
        throw new Error('Failed to generate report content');
      }
    } catch (err) {
      console.error('Error generating report:', err);
      setError(err instanceof Error ? err.message : 'There was an error generating your report. Please try again.');
      setShowError(true);
    } finally {
      setIsGenerating(false);
    }
  };

  // Handler for finalizing and downloading the report
  const handleFinalizeReport = async () => {
    if (!reportId) {
      setError('No report ID found. Please upload documents and generate a report first.');
      setShowError(true);
      return;
    }
    
    setIsDownloading(true);
    setError(null);
    
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
    } catch (err) {
      console.error('Error in report finalization/download process:', err);
      
      const errorMessage = err instanceof Error 
        ? `There was an error downloading your report: ${err.message}`
        : 'There was an error downloading your report. Please try again.';
      
      setError(errorMessage);
      setShowError(true);
    } finally {
      setIsDownloading(false);
    }
  };
  
  const handleCloseError = () => {
    setShowError(false);
  };

  // Handler for downloading the finalized PDF
  const handleDownloadPDF = async () => {
    try {
      setIsDownloading(true);
      await downloadReport(reportId);
      setIsDownloading(false);
    } catch (error) {
      console.error("Error downloading report:", error);
      setIsDownloading(false);
      alert("There was an error downloading your report. Please try again.");
    }
  };

  return (
    <div>
      <Navbar />
      <Container maxWidth="lg" sx={{ py: 5 }}>
        <Box 
          sx={{ 
            textAlign: 'center', 
            mb: 5,
            maxWidth: 800,
            mx: 'auto'
          }}
        >
          <Typography 
            variant="h2" 
            component="h1" 
            sx={{ 
              fontWeight: 600, 
              mb: 2,
              fontSize: { xs: '2rem', sm: '2.5rem', md: '3rem' } 
            }}
          >
            Generatore di Perizie
          </Typography>
          <Typography 
            variant="h5" 
            color="text.secondary" 
            sx={{ 
              mb: 3,
              fontWeight: 400,
              fontSize: { xs: '1rem', sm: '1.25rem' } 
            }}
          >
            Carica i tuoi documenti e l'AI genererà un report formattato per te
          </Typography>
        </Box>
        
        <Stepper 
          activeStep={activeStep} 
          alternativeLabel 
          sx={{ 
            mb: 5,
            '& .MuiStepLabel-root .Mui-completed': {
              color: 'success.main', 
            },
            '& .MuiStepLabel-root .Mui-active': {
              color: 'primary.main', 
            } 
          }}
        >
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
        
        {activeStep === 0 && (
          <FileUpload onUploadSuccess={handleUploadSuccess} />
        )}
        
        {activeStep === 1 && (
          <Paper 
            sx={{ 
              p: 4, 
              mb: 4, 
              borderRadius: 3,
              background: 'linear-gradient(145deg, rgba(255,255,255,1) 0%, rgba(249,249,252,1) 100%)'
            }}
          >
            <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
              Edit Report
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
              Revisiona e modifica il report generato dall'AI prima di finalizzarlo.
            </Typography>
            <TextField
              fullWidth
              multiline
              rows={14}
              variant="outlined"
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              InputProps={{
                sx: {
                  fontFamily: 'SF Mono, Menlo, Monaco, Consolas, monospace',
                  fontSize: '0.9rem',
                  lineHeight: 1.6,
                  borderRadius: 2
                }
              }}
              sx={{ mb: 3 }}
            />
            <Button
              variant="contained"
              color="primary"
              size="large"
              onClick={handleFinalizeReport}
              disabled={isGenerating}
              sx={{ 
                py: 1.5,
                px: 4,
                position: 'relative'
              }}
            >
              {isGenerating ? (
                <>
                  <CircularProgress 
                    size={24} 
                    color="inherit" 
                    sx={{ 
                      position: 'absolute',
                      left: 'calc(50% - 12px)'
                    }} 
                  />
                  <span style={{ opacity: 0 }}>Finalizing...</span>
                </>
              ) : "Finalize Report"}
            </Button>
          </Paper>
        )}
        
        {activeStep === 2 && (
          <Paper 
            sx={{ 
              p: 4, 
              mb: 4, 
              borderRadius: 3,
              background: 'linear-gradient(145deg, rgba(255,255,255,1) 0%, rgba(249,249,252,1) 100%)'
            }}
          >
            <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
              Download Report
            </Typography>
            <Typography variant="body1" sx={{ mb: 4, color: 'text.secondary' }}>
              Il tuo report è stato generato con successo e pronto per il download.
            </Typography>
            
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
              <Button
                variant="contained"
                color="primary"
                size="large"
                onClick={handleDownloadPDF}
                disabled={isDownloading}
                startIcon={<CloudDownloadIcon />}
                sx={{ 
                  py: 1.5,
                  px: 4,
                  position: 'relative'
                }}
              >
                {isDownloading ? (
                  <>
                    <CircularProgress 
                      size={24} 
                      color="inherit" 
                      sx={{ 
                        position: 'absolute',
                        left: 'calc(50% - 12px)'
                      }} 
                    />
                    <span style={{ opacity: 0 }}>Downloading...</span>
                  </>
                ) : "Download PDF"}
              </Button>
            </Box>
            
            <Typography variant="body2" align="center" color="text.secondary">
              Report ID: {reportId}
            </Typography>
          </Paper>
        )}
      </Container>
      <Snackbar
        open={showError}
        autoHideDuration={6000}
        onClose={handleCloseError}
      >
        <Alert onClose={handleCloseError} severity="error">
          {error}
        </Alert>
      </Snackbar>
    </div>
  );
} 