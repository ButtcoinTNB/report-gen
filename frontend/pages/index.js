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
  CardContent,
  Chip,
  Fade
} from '@mui/material';
import CloudDownloadIcon from '@mui/icons-material/CloudDownload';
import ChatIcon from '@mui/icons-material/Chat';
import EditIcon from '@mui/icons-material/Edit';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DownloadIcon from '@mui/icons-material/Download';
import Navbar from '../components/Navbar';
import FileUpload from '../components/FileUpload';
import { generateReport, refineReport, analyzeDocuments } from '../api/generate.js';
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
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [analysisInProgress, setAnalysisInProgress] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [infoReady, setInfoReady] = useState(false);
  
  // Updated steps for new workflow
  const steps = [
    'Carica Documenti', 
    'Aggiungi Informazioni', 
    'Anteprima e Modifica', 
    'Scarica'
  ];

  const handleUploadSuccess = async (reportId) => {
    // Update activeStep and reportId
    setReportId(reportId);
    setActiveStep(1); // Go directly to InfoForm
    
    // Reset states
    setAnalysisComplete(false);
    setAnalysisInProgress(true);
    setFieldsNeedingAttention([]);
    setExtractedVariables({});
    
    // Start the analysis in the background
    analyzeDocumentsInBackground(reportId);
  };
  
  // Analyze documents in the background
  const analyzeDocumentsInBackground = async (id) => {
    try {
      // Use the analyzeDocuments function from the imported API
      const response = await analyzeDocuments(id);
      
      console.log('Document analysis result:', response);
      
      if (response && response.extracted_variables) {
        setExtractedVariables(response.extracted_variables);
        setFieldsNeedingAttention(response.fields_needing_attention || []);
      }
      
      setAnalysisComplete(true);
    } catch (err) {
      console.error('Error analyzing documents:', err);
      setError('Analisi completata con alcuni problemi. Puoi comunque procedere.');
      setShowError(true);
    } finally {
      setAnalysisInProgress(false);
    }
  };

  // Helper function to extract error messages from different response formats
  const extractErrorMessage = (error) => {
    if (!error) return null;
    
    // Handle different error formats
    if (typeof error === 'string') return error;
    
    if (error.response && error.response.data) {
      const data = error.response.data;
      
      if (typeof data === 'string') return data;
      if (data.detail) return data.detail;
      if (data.message) return data.message;
      if (data.error) return typeof data.error === 'string' ? data.error : 'Errore del server';
      if (data.errorMessage) return data.errorMessage;
    }
    
    return error.message || 'Si è verificato un errore sconosciuto';
  };

  // Handler for submitting additional information
  const handleInfoSubmit = async () => {
    if (!reportId) {
      setError('Nessun ID report trovato. Carica prima i documenti.');
      setShowError(true);
      return;
    }
    
    setIsGenerating(true);
    setError(null);
    setShowFeedback(false);
    
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
        throw new Error('Impossibile generare l\'anteprima del report');
      }
    } catch (err) {
      console.error('Error generating report:', err);
      
      // Improved error handling to extract string message from various error formats
      let errorMessage = 'Si è verificato un errore durante la generazione del report. Riprova.';
      
      if (err.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        if (err.response.data) {
          const responseData = err.response.data;
          
          if (typeof responseData === 'string') {
            errorMessage = responseData;
          } else if (responseData.detail) {
            errorMessage = responseData.detail;
          } else if (responseData.message) {
            errorMessage = responseData.message;
          } else if (responseData.error) {
            errorMessage = typeof responseData.error === 'string' 
              ? responseData.error 
              : 'Si è verificato un errore sul server';
          }
        }
      } else if (err.message) {
        // Something happened in setting up the request that triggered an Error
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      setShowError(true);
    } finally {
      setIsGenerating(false);
    }
  };

  // Handle retry after error
  const handleRetry = () => {
    setShowError(false);
    setError(null);
    handleInfoSubmit();
  };

  // Handler for chat interaction
  const handleChatSubmit = async () => {
    if (!chatInput.trim()) return;
    
    // Add user message to chat
    const userMessage = { role: 'user', content: chatInput };
    setChatMessages(prevMessages => [...prevMessages, userMessage]);
    setChatInput('');
    setShowFeedback(false);
    
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
        
        // Show feedback request
        setShowFeedback(true);
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
      
      // Improved error handling similar to handleInfoSubmit
      let uiErrorMessage = 'Errore durante il perfezionamento del report: Errore sconosciuto';
      
      if (err.response && err.response.data) {
        const responseData = err.response.data;
        if (typeof responseData === 'string') {
          uiErrorMessage = 'Errore durante il perfezionamento del report: ' + responseData;
        } else if (responseData.detail) {
          uiErrorMessage = 'Errore durante il perfezionamento del report: ' + responseData.detail;
        } else if (responseData.message) {
          uiErrorMessage = 'Errore durante il perfezionamento del report: ' + responseData.message;
        } else if (responseData.error) {
          uiErrorMessage = 'Errore durante il perfezionamento del report: ' + (typeof responseData.error === 'string' 
            ? responseData.error 
            : 'Si è verificato un errore sul server');
        }
      } else if (err.message) {
        uiErrorMessage = 'Errore durante il perfezionamento del report: ' + err.message;
      }
      
      setError(uiErrorMessage);
      setShowError(true);
    } finally {
      setIsGenerating(false);
    }
  };
  
  // Handler for the "Approve Report" action
  const handleApproveReport = () => {
    handleFinalizeReport();
  };
  
  // Handler for the "Download Current Version" action
  const handleDownloadCurrentVersion = async () => {
    if (!reportId) {
      setError('Nessun ID report trovato. Genera prima un report.');
      setShowError(true);
      return;
    }
    
    try {
      setIsDownloading(true);
      const result = await downloadReport(reportId);
      
      if (result && result.data && result.data.download_url) {
        window.open(result.data.download_url, '_blank');
      } else {
        throw new Error('Impossibile ottenere l\'URL di download');
      }
    } catch (err) {
      console.error('Error downloading report:', err);
      setError('Errore durante il download del report: ' + (err.message || 'Errore sconosciuto'));
      setShowError(true);
    } finally {
      setIsDownloading(false);
    }
  };
  
  // Handler for the "Looks Good" feedback
  const handlePositiveFeedback = () => {
    setShowFeedback(false);
    const feedbackMessage = { 
      role: 'user', 
      content: 'Le modifiche sembrano buone. Grazie!' 
    };
    setChatMessages(prevMessages => [...prevMessages, feedbackMessage]);
  };
  
  // Handler for the "Still Needs Changes" feedback
  const handleNegativeFeedback = () => {
    setShowFeedback(false);
    setChatInput('Le modifiche non sono ancora perfette. Vorrei che tu ');
    // Focus the chat input
    setTimeout(() => {
      document.querySelector('input[type="text"]')?.focus();
    }, 100);
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
            <Typography variant="body1" sx={{ mb: 2, color: 'text.secondary' }}>
              Fornisci eventuali informazioni aggiuntive non presenti nei documenti caricati.
            </Typography>
            
            {/* Analysis in progress indicator */}
            {analyzeLoading && (
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, p: 2, bgcolor: 'rgba(3, 169, 244, 0.05)', borderRadius: 2 }}>
                <CircularProgress size={24} sx={{ mr: 2 }} />
                <Typography>
                  Analisi dei documenti in corso... Puoi iniziare ad aggiungere informazioni nel frattempo.
                </Typography>
              </Box>
            )}
            
            {/* Analysis complete notification */}
            {analysisComplete && (
              <Fade in={analysisComplete}>
                <Box sx={{ mb: 3, p: 2, bgcolor: 'rgba(76, 175, 80, 0.05)', borderRadius: 2, display: 'flex', alignItems: 'center' }}>
                  <CheckCircleIcon color="success" sx={{ mr: 2 }} />
                  <Typography>
                    Analisi completata! Abbiamo estratto le informazioni dai tuoi documenti.
                  </Typography>
                </Box>
              </Fade>
            )}
            
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
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">
                      Anteprima del Report
                    </Typography>
                    
                    {/* Download current version button */}
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<DownloadIcon />}
                      onClick={handleDownloadCurrentVersion}
                      disabled={isDownloading || !previewHtml}
                    >
                      Scarica Versione Attuale
                    </Button>
                  </Box>
                  
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
                
                {/* Like/Dislike action buttons */}
                <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mb: 3 }}>
                  <Button
                    variant="contained"
                    color="success"
                    size="large"
                    startIcon={<ThumbUpIcon />}
                    onClick={handleApproveReport}
                    disabled={!previewHtml || isDownloading}
                  >
                    Approva Report
                  </Button>
                  <Button
                    variant="contained"
                    color="primary"
                    size="large"
                    startIcon={<ThumbDownIcon />}
                    onClick={handleNegativeFeedback}
                    disabled={!previewHtml || isGenerating}
                  >
                    Richiedi Modifiche
                  </Button>
                </Box>
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
                    
                    {/* Feedback Request */}
                    {showFeedback && (
                      <Box 
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          maxWidth: '85%',
                          alignSelf: 'flex-start',
                          bgcolor: 'rgba(3, 169, 244, 0.1)',
                          mt: 2
                        }}
                      >
                        <Typography variant="body2" gutterBottom>
                          Cosa ne pensi delle modifiche?
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                          <Button 
                            size="small" 
                            variant="outlined"
                            color="success"
                            onClick={handlePositiveFeedback}
                          >
                            Sembra buono
                          </Button>
                          <Button 
                            size="small" 
                            variant="outlined"
                            color="primary"
                            onClick={handleNegativeFeedback}
                          >
                            Servono altre modifiche
                          </Button>
                        </Box>
                      </Box>
                    )}
                    
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
          <Alert 
            onClose={handleCloseError} 
            severity="error" 
            sx={{ width: '100%' }}
            action={
              <Button 
                color="inherit" 
                size="small" 
                onClick={handleRetry}
              >
                Riprova
              </Button>
            }
          >
            {error}
          </Alert>
        </Snackbar>
      </Container>
    </div>
  );
} 