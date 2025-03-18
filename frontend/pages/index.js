// Trigger Vercel redeploy - Updated on: 2024-03-19
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
  Snackbar,
  Grid,
  Card,
  CardContent
} from '@mui/material';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import ChatIcon from '@mui/icons-material/Chat';
import EditIcon from '@mui/icons-material/Edit';
import Navbar from '../components/Navbar';
import FileUpload from '../components/FileUpload';
import { generateReport, refineReport } from '../api/generate.js';
import { finalizeReport, downloadReport } from '../api/report';
import axios from 'axios';
import { config } from '../config';

export default function Home() {
  const [activeStep, setActiveStep] = useState(0);
  const [reportId, setReportId] = useState(null);
  const [additionalInfo, setAdditionalInfo] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [editedText, setEditedText] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [error, setError] = useState(null);
  const [showError, setShowError] = useState(false);
  const [extractedVariables, setExtractedVariables] = useState({});
  const [fieldsNeedingAttention, setFieldsNeedingAttention] = useState([]);
  
  // Updated steps for new workflow
  const steps = [
    'Upload Documents', 
    'Add Information', 
    'Preview & Edit Report', 
    'Download'
  ];

  // Handler for upload success
  const handleUploadSuccess = async (id) => {
    console.log('Upload success with report ID:', id);
    setReportId(id);
    setError(null);
    
    // Move to the Additional Info step
    setActiveStep(1);
    
    // Analyze documents to extract variables
    try {
      setIsGenerating(true);
      const response = await axios.post(`${config.endpoints.generate}/analyze`, {
        document_ids: [id],
        additional_info: ''
      });
      
      console.log('Document analysis result:', response.data);
      
      if (response.data && response.data.extracted_variables) {
        setExtractedVariables(response.data.extracted_variables);
        setFieldsNeedingAttention(response.data.fields_needing_attention || []);
      }
    } catch (err) {
      console.error('Error analyzing documents:', err);
      setError('Failed to analyze documents. Please try again.');
      setShowError(true);
    } finally {
      setIsGenerating(false);
    }
  };

  // Handler for submitting additional information
  const handleInfoSubmit = async () => {
    if (!reportId) {
      setError('No report ID found. Please upload documents first.');
      setShowError(true);
      return;
    }
    
    setIsGenerating(true);
    setError(null);
    
    try {
      // Generate report with additional info
      const result = await axios.post(`${config.endpoints.generate}/generate`, {
        document_ids: [reportId],
        additional_info: additionalInfo
      });
      
      console.log('Report generation result:', result.data);
      
      if (result.data && result.data.report_id) {
        // Store the new report ID
        setReportId(result.data.report_id);
        
        // Fetch the HTML preview
        const previewUrl = result.data.preview_url;
        if (previewUrl) {
          const previewResponse = await axios.get(previewUrl);
          setPreviewHtml(previewResponse.data);
        }
        
        // Initialize chat with a system message
        setChatMessages([
          { 
            role: 'system', 
            content: 'Il report è stato generato. Puoi fare domande o richiedere modifiche.' 
          }
        ]);
        
        // Move to the Preview & Edit step
        setActiveStep(2);
      } else {
        throw new Error('Failed to generate report preview');
      }
    } catch (err) {
      console.error('Error generating report:', err);
      setError(err.response?.data?.detail || err.message || 'There was an error generating your report. Please try again.');
      setShowError(true);
    } finally {
      setIsGenerating(false);
    }
  };

  // Handler for chat interaction
  const handleChatSubmit = async () => {
    if (!chatInput.trim()) return;
    
    // Add user message to chat
    const userMessage = { role: 'user', content: chatInput };
    setChatMessages(prevMessages => [...prevMessages, userMessage]);
    setChatInput('');
    
    try {
      setIsGenerating(true);
      
      // Call the refine endpoint
      const result = await refineReport(reportId, chatInput);
      
      if (result && !result.error) {
        // Add AI response to chat
        const aiMessage = { 
          role: 'assistant', 
          content: 'Ho aggiornato il report in base alle tue istruzioni.' 
        };
        setChatMessages(prevMessages => [...prevMessages, aiMessage]);
        
        // Update report ID if a new one was returned
        if (result.report_id) {
          setReportId(result.report_id);
        }
        
        // Fetch updated preview
        if (result.preview_url) {
          const previewResponse = await axios.get(result.preview_url);
          setPreviewHtml(previewResponse.data);
        }
      } else {
        // Add error message to chat
        const errorMessage = { 
          role: 'assistant', 
          content: 'Mi dispiace, non sono riuscito ad applicare le modifiche richieste. Puoi riprovare con istruzioni diverse?' 
        };
        setChatMessages(prevMessages => [...prevMessages, errorMessage]);
      }
    } catch (err) {
      console.error('Error refining report:', err);
      
      // Add error message to chat
      const errorMessage = { 
        role: 'assistant', 
        content: 'Si è verificato un errore durante l\'elaborazione della tua richiesta. Puoi riprovare?' 
      };
      setChatMessages(prevMessages => [...prevMessages, errorMessage]);
      
      setError('Error refining report: ' + (err.message || 'Unknown error'));
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
      // Download the report directly from the download URL
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
        setActiveStep(3);
      } else {
        throw new Error('Failed to get download URL');
      }
    } catch (err) {
      console.error('Error downloading report:', err);
      
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
        
        {/* Step 1: Upload Documents */}
        {activeStep === 0 && (
          <FileUpload onUploadSuccess={handleUploadSuccess} />
        )}
        
        {/* Step 2: Additional Information */}
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
              Informazioni Aggiuntive
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
              Fornisci eventuali informazioni aggiuntive non presenti nei documenti caricati.
            </Typography>
            
            {fieldsNeedingAttention.length > 0 && (
              <Box sx={{ mb: 4 }}>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 500 }}>
                  Campi che potrebbero richiedere la tua attenzione:
                </Typography>
                <Grid container spacing={2}>
                  {fieldsNeedingAttention.map((field, index) => (
                    <Grid item xs={12} sm={6} md={4} key={index}>
                      <Card variant="outlined" sx={{ bgcolor: 'rgba(255,152,0,0.05)' }}>
                        <CardContent>
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                            {field}
                          </Typography>
                          <Typography variant="body2">
                            {extractedVariables[field]?.value || 'Non rilevato'}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </Box>
            )}
            
            <TextField
              fullWidth
              multiline
              rows={8}
              variant="outlined"
              placeholder="Esempio: Il numero di polizza corretto è 12345678. L'importo del danno è di €10.000."
              label="Informazioni aggiuntive o correzioni"
              value={additionalInfo}
              onChange={(e) => setAdditionalInfo(e.target.value)}
              InputProps={{
                sx: {
                  fontFamily: 'inherit',
                  fontSize: '1rem',
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
              onClick={handleInfoSubmit}
              disabled={isGenerating}
              sx={{ 
                py: 1.5,
                px: 4,
                position: 'relative',
                minWidth: 200
              }}
            >
              {isGenerating ? (
                <>
                  <CircularProgress
                    size={24}
                    sx={{
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      marginTop: '-12px',
                      marginLeft: '-12px',
                    }}
                  />
                  <span style={{ opacity: 0 }}>Genera Report</span>
                </>
              ) : (
                'Genera Report'
              )}
            </Button>
          </Paper>
        )}
        
        {/* Step 3: Preview & Edit with Chat */}
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
              Anteprima e Modifica Report
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
              Visualizza l'anteprima del report e chatta con l'AI per apportare modifiche.
            </Typography>
            
            <Grid container spacing={3}>
              {/* Preview Panel */}
              <Grid item xs={12} md={7}>
                <Paper 
                  elevation={0} 
                  variant="outlined" 
                  sx={{ 
                    p: 3, 
                    mb: 3, 
                    maxHeight: '60vh', 
                    overflow: 'auto',
                    borderRadius: 2
                  }}
                >
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Anteprima del Report
                  </Typography>
                  
                  {previewHtml ? (
                    <Box
                      sx={{
                        '& img': { maxWidth: '100%' },
                        '& table': { width: '100%', borderCollapse: 'collapse' },
                        '& th, & td': { border: '1px solid #ddd', padding: '8px' }
                      }}
                      dangerouslySetInnerHTML={{ __html: previewHtml }}
                    />
                  ) : (
                    <Box sx={{ textAlign: 'center', p: 4 }}>
                      <CircularProgress size={40} />
                      <Typography sx={{ mt: 2 }}>Caricamento anteprima...</Typography>
                    </Box>
                  )}
                </Paper>
              </Grid>
              
              {/* Chat Panel */}
              <Grid item xs={12} md={5}>
                <Paper 
                  elevation={0} 
                  variant="outlined" 
                  sx={{ 
                    p: 3, 
                    height: '60vh', 
                    display: 'flex',
                    flexDirection: 'column',
                    borderRadius: 2
                  }}
                >
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Chat con l'AI per Modifiche
                  </Typography>
                  
                  {/* Chat Messages */}
                  <Box 
                    sx={{ 
                      flexGrow: 1, 
                      overflow: 'auto',
                      mb: 2,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 1.5
                    }}
                  >
                    {chatMessages.filter(msg => msg.role !== 'system').map((message, index) => (
                      <Box 
                        key={index}
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          maxWidth: '85%',
                          alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
                          bgcolor: message.role === 'user' ? 'primary.light' : 'grey.100',
                          color: message.role === 'user' ? 'white' : 'text.primary'
                        }}
                      >
                        <Typography variant="body2">
                          {message.content}
                        </Typography>
                      </Box>
                    ))}
                    {isGenerating && (
                      <Box 
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          maxWidth: '85%',
                          alignSelf: 'flex-start',
                          bgcolor: 'grey.100'
                        }}
                      >
                        <CircularProgress size={20} sx={{ mr: 1 }} />
                        <Typography variant="body2" component="span">
                          Elaborazione...
                        </Typography>
                      </Box>
                    )}
                  </Box>
                  
                  {/* Chat Input */}
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <TextField
                      fullWidth
                      variant="outlined"
                      size="small"
                      placeholder="Chiedi una modifica o fornisci istruzioni..."
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleChatSubmit()}
                      disabled={isGenerating}
                    />
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={handleChatSubmit}
                      disabled={isGenerating || !chatInput.trim()}
                      startIcon={<ChatIcon />}
                    >
                      Invia
                    </Button>
                  </Box>
                </Paper>
              </Grid>
            </Grid>
            
            <Box sx={{ mt: 4, display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="contained"
                color="primary"
                size="large"
                onClick={handleFinalizeReport}
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
                      sx={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        marginTop: '-12px',
                        marginLeft: '-12px',
                      }}
                    />
                    <span style={{ opacity: 0 }}>Scarica Report</span>
                  </>
                ) : (
                  'Scarica Report'
                )}
              </Button>
            </Box>
          </Paper>
        )}
        
        {/* Step 4: Final Download */}
        {activeStep === 3 && (
          <Paper 
            sx={{ 
              p: 4, 
              mb: 4, 
              borderRadius: 3,
              textAlign: 'center'
            }}
          >
            <Typography variant="h4" sx={{ mb: 3, fontWeight: 600 }}>
              Report Completato
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
              Il tuo report è stato generato con successo e dovrebbe essere stato scaricato automaticamente.
            </Typography>
            <Button
              variant="contained"
              color="primary"
              size="large"
              onClick={() => window.open(downloadUrl, '_blank')}
              startIcon={<CloudDownloadIcon />}
              sx={{ 
                py: 1.5,
                px: 4,
                minWidth: 200
              }}
            >
              Scarica di Nuovo
            </Button>
          </Paper>
        )}
        
        <Snackbar 
          open={showError} 
          autoHideDuration={6000} 
          onClose={handleCloseError}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert onClose={handleCloseError} severity="error" sx={{ width: '100%' }}>
            {error}
          </Alert>
        </Snackbar>
      </Container>
    </div>
  );
} 