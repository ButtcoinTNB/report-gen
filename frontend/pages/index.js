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
import LoadingIndicator from '../components/LoadingIndicator';

export default function Home() {
  const [activeStep, setActiveStep] = useState(0);
  const [reportId, setReportId] = useState(null);
  const [additionalInfo, setAdditionalInfo] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [editedText, setEditedText] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [loadingState, setLoadingState] = useState({
    isLoading: false,
    progress: 0,
    stage: 'initial',
    message: ''
  });
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [error, setError] = useState(null);
  const [showError, setShowError] = useState(false);
  const [extractedVariables, setExtractedVariables] = useState({});
  const [fieldsNeedingAttention, setFieldsNeedingAttention] = useState([]);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
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
    setLoadingState({
      isLoading: true,
      progress: 0,
      stage: 'analyzing',
      message: 'Analisi dei documenti in corso...'
    });
    setFieldsNeedingAttention([]);
    setExtractedVariables({});
    
    // Start the analysis in the background
    analyzeDocumentsInBackground(reportId);
  };
  
  // Analyze documents in the background
  const analyzeDocumentsInBackground = async (id) => {
    try {
      // Use the analyzeDocuments function from the imported API
      const response = await analyzeDocuments(id, (progress) => {
        setLoadingState(prevState => ({
          ...prevState,
          progress,
          message: `Analisi: ${progress}%`
        }));
      });
      
      console.log('Document analysis result:', response);
      
      if (response && response.extracted_variables) {
        setExtractedVariables(response.extracted_variables);
        setFieldsNeedingAttention(response.fields_needing_attention || []);
      }
      
      setAnalysisComplete(true);
      setLoadingState({
        isLoading: false,
        progress: 100,
        stage: 'completed',
        message: 'Analisi completata con successo!'
      });
    } catch (err) {
      console.error('Error analyzing documents:', err);
      setError('Analisi completata con alcuni problemi. Puoi comunque procedere.');
      setShowError(true);
      setLoadingState({
        isLoading: false,
        stage: 'error',
        error: err.message || 'Errore durante l\'analisi',
        message: 'Si è verificato un problema durante l\'analisi'
      });
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
    
    setLoadingState({
      isLoading: true,
      progress: 0,
      stage: 'generating',
      message: 'Generazione del report in corso...'
    });
    setError(null);
    setShowFeedback(false);
    
    try {
      // Generate report with additional info
      const result = await generateReport(reportId, {
        additional_info: additionalInfo
      }, (progress) => {
        setLoadingState(prevState => ({
          ...prevState,
          progress,
          message: `Generazione: ${progress}%`
        }));
      });
      
      console.log('Report generation result:', result);
      
      if (result && result.report_id) {
        // Store the new report ID
        setReportId(result.report_id);
        
        // Fetch the HTML preview
        const previewUrl = result.preview_url;
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
        
        setLoadingState({
          isLoading: false,
          progress: 100,
          stage: 'completed',
          message: 'Report generato con successo!'
        });
      } else {
        throw new Error('Impossibile generare l\'anteprima del report');
      }
    } catch (err) {
      console.error('Error generating report:', err);
      
      // Extract error message from various formats
      const errorMessage = extractErrorMessage(err);
      
      setError(errorMessage);
      setShowError(true);
      setLoadingState({
        isLoading: false,
        stage: 'error',
        error: errorMessage,
        message: 'Si è verificato un problema durante la generazione'
      });
    }
  };

  // Handle retry after error
  const handleRetry = () => {
    setShowError(false);
    setError(null);
    setLoadingState({
      isLoading: false,
      progress: 0,
      stage: 'initial'
    });
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
      setLoadingState({
        isLoading: true,
        progress: 0,
        stage: 'refining',
        message: 'Affinamento del report in corso...'
      });
      
      // Call the refine endpoint
      const result = await refineReport(reportId, chatInput, (progress) => {
        setLoadingState(prevState => ({
          ...prevState,
          progress,
          message: `Affinamento: ${progress}%`
        }));
      });
      
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
        
        setLoadingState({
          isLoading: false,
          progress: 100,
          stage: 'completed',
          message: 'Report affinato con successo!'
        });
      } else {
        // Add error message to chat
        const errorMessage = { 
          role: 'system', 
          content: result.error || 'Si è verificato un errore durante l\'elaborazione della richiesta.'
        };
        setChatMessages(prevMessages => [...prevMessages, errorMessage]);
        
        setLoadingState({
          isLoading: false,
          stage: 'error',
          error: result.error || 'Errore durante l\'affinamento',
          message: 'Si è verificato un problema durante l\'affinamento'
        });
      }
    } catch (err) {
      console.error('Error refining report:', err);
      
      // Add error message to chat
      const errMsg = extractErrorMessage(err);
      const errorChatMessage = { 
        role: 'system', 
        content: `Errore: ${errMsg}`
      };
      setChatMessages(prevMessages => [...prevMessages, errorChatMessage]);
      
      setLoadingState({
        isLoading: false,
        stage: 'error',
        error: errMsg,
        message: 'Si è verificato un problema durante l\'affinamento'
      });
    }
  };
  
  // Handler for the "Approve Report" action
  const handleApproveReport = () => {
    handleFinalizeReport();
  };
  
  // Handler for the "Download Current Version" action
  const handleDownloadCurrentVersion = async () => {
    if (!reportId) {
      setError('Nessun ID report trovato. Impossibile scaricare.');
      setShowError(true);
      return;
    }
    
    setLoadingState({
      isLoading: true,
      progress: 0,
      stage: 'loading',
      message: 'Preparazione del download...'
    });
    
    try {
      const downloadResult = await downloadReport(reportId);
      
      if (downloadResult && downloadResult.download_url) {
        // Redirect to download URL
        window.location.href = downloadResult.download_url;
        
        // Show a success message
        setTimeout(() => {
          alert('Nota: I documenti caricati e i relativi dati verranno eliminati dal server dopo il download.');
        }, 1000);
        
        setLoadingState({
          isLoading: false,
          progress: 100,
          stage: 'completed',
          message: 'Download avviato con successo!'
        });
      } else {
        throw new Error('URL di download non disponibile');
      }
    } catch (err) {
      console.error('Error downloading report:', err);
      setError(extractErrorMessage(err) || 'Si è verificato un errore durante il download.');
      setShowError(true);
      
      setLoadingState({
        isLoading: false,
        stage: 'error',
        error: extractErrorMessage(err),
        message: 'Si è verificato un problema durante il download'
      });
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
    
    setLoadingState({
      isLoading: true,
      progress: 0,
      stage: 'finalizing',
      message: 'Finalizzazione del report in corso...'
    });
    
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
        
        setLoadingState({
          isLoading: false,
          progress: 100,
          stage: 'completed',
          message: 'Report finalizzato con successo!'
        });
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
      setLoadingState({
        isLoading: false,
        stage: 'error',
        error: errorMessage,
        message: 'Si è verificato un problema durante la finalizzazione'
      });
    }
  };
  
  const handleCloseError = () => {
    setShowError(false);
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <Container className="flex-grow py-8">
        <Box mb={4}>
          <Typography variant="h4" gutterBottom align="center">
            Generatore Automatico di Perizie
          </Typography>
          <Typography variant="subtitle1" color="textSecondary" align="center" gutterBottom>
            Carica i tuoi documenti e genera report strutturati basati sul loro contenuto
          </Typography>
        </Box>

        <Box mb={6}>
          <Stepper activeStep={activeStep} alternativeLabel>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        {/* Display our new LoadingIndicator component */}
        <LoadingIndicator 
          state={loadingState}
          variant="linear"
          onRetry={handleRetry}
          showAlways={loadingState.stage !== 'initial'}
        />

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
              disabled={loadingState.isLoading}
              sx={{ 
                py: 1.5,
                px: 4,
                position: 'relative',
                minWidth: 200
              }}
            >
              {loadingState.isLoading ? (
                <>
                  <LoadingIndicator 
                    state={loadingState}
                    variant="circular"
                    size={24}
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
                      disabled={loadingState.isLoading || !previewHtml}
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
                      <LoadingIndicator 
                        state={loadingState}
                        variant="circular"
                        size={40}
                      />
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
                    disabled={!previewHtml || loadingState.isLoading}
                  >
                    Approva Report
                  </Button>
                  <Button
                    variant="contained"
                    color="primary"
                    size="large"
                    startIcon={<ThumbDownIcon />}
                    onClick={handleNegativeFeedback}
                    disabled={!previewHtml || loadingState.isLoading}
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
                    
                    {loadingState.isLoading && (
                      <Box 
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          maxWidth: '85%',
                          alignSelf: 'flex-start',
                          bgcolor: 'grey.100'
                        }}
                      >
                        <LoadingIndicator 
                          state={loadingState}
                          variant="circular"
                          size={20}
                        />
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
                      disabled={loadingState.isLoading}
                    />
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={handleChatSubmit}
                      disabled={loadingState.isLoading || !chatInput.trim()}
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