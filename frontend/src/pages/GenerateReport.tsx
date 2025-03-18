import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Alert,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import DocumentUpload from '../components/DocumentUpload';
import AdditionalInfo from '../components/AdditionalInfo';
import { analyzeDocuments, generateReport, refineReport } from '../services/api';

type Step = 'upload' | 'additional-info' | 'preview';

interface AnalysisDetails {
  valore: string;
  confidenza: 'ALTA' | 'MEDIA' | 'BASSA';
  richiede_verifica: boolean;
}

interface AnalysisResponse {
  extractedVariables: Record<string, string>;
  analysisDetails: Record<string, AnalysisDetails>;
  fieldsNeedingAttention: string[];
}

interface ReportPreview {
  previewUrl: string;
  downloadUrl: string;
  reportId: string;
}

const GenerateReport: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<Step>('upload');
  const [documentIds, setDocumentIds] = useState<string[]>([]);
  const [analysisResponse, setAnalysisResponse] = useState<AnalysisResponse | null>(null);
  const [reportPreview, setReportPreview] = useState<ReportPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showInstructionsDialog, setShowInstructionsDialog] = useState(false);
  const [instructions, setInstructions] = useState('');

  const handleDocumentsUploaded = async (ids: string[]) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await analyzeDocuments(ids);
      setAnalysisResponse(response);
      setDocumentIds(ids);
      setCurrentStep('additional-info');
    } catch (err) {
      setError('Si è verificato un errore durante l\'analisi dei documenti. Riprova.');
      console.error('Error analyzing documents:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAdditionalInfo = async (additionalInfo: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const preview = await generateReport({
        documentIds,
        additionalInfo,
      });
      setReportPreview(preview);
      setCurrentStep('preview');
    } catch (err) {
      setError('Si è verificato un errore durante la generazione del report. Riprova.');
      console.error('Error generating report:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefineReport = async () => {
    if (!instructions.trim() || !reportPreview?.reportId) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const preview = await refineReport(reportPreview.reportId, instructions);
      setReportPreview(preview);
      setShowInstructionsDialog(false);
      setInstructions('');
    } catch (err) {
      setError('Si è verificato un errore durante la modifica del report. Riprova.');
      console.error('Error refining report:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBack = () => {
    if (currentStep === 'additional-info') {
      setCurrentStep('upload');
    } else if (currentStep === 'preview') {
      setCurrentStep('additional-info');
    }
  };

  const steps = [
    { label: 'Carica Documenti', completed: currentStep !== 'upload' },
    { label: 'Revisiona e Aggiungi Informazioni', completed: currentStep === 'preview' },
    { label: 'Anteprima Report', completed: false },
  ];

  const handleDownload = () => {
    if (reportPreview?.downloadUrl) {
      window.location.href = reportPreview.downloadUrl;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Generazione Report
        </Typography>
        <Stepper activeStep={steps.findIndex(s => !s.completed)} sx={{ mb: 4 }}>
          {steps.map((step, index) => (
            <Step key={index} completed={step.completed}>
              <StepLabel>{step.label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {!isLoading && currentStep === 'upload' && (
        <DocumentUpload
          onUploadComplete={handleDocumentsUploaded}
          isLoading={isLoading}
        />
      )}

      {!isLoading && currentStep === 'additional-info' && analysisResponse && (
        <AdditionalInfo
          documentIds={documentIds}
          extractedVariables={analysisResponse.extractedVariables}
          analysisDetails={analysisResponse.analysisDetails}
          fieldsNeedingAttention={analysisResponse.fieldsNeedingAttention}
          onSubmit={handleAdditionalInfo}
          onBack={handleBack}
        />
      )}

      {!isLoading && currentStep === 'preview' && reportPreview && (
        <Box>
          <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h5">
              Anteprima Report
            </Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="outlined"
                onClick={() => setShowInstructionsDialog(true)}
              >
                Modifica Report
              </Button>
              <Button
                variant="contained"
                onClick={handleDownload}
              >
                Scarica DOCX
              </Button>
            </Box>
          </Box>

          <Box sx={{ width: '100%', height: '600px', border: '1px solid rgba(0, 0, 0, 0.12)', borderRadius: 1 }}>
            <iframe
              src={reportPreview.previewUrl}
              style={{ width: '100%', height: '100%', border: 'none' }}
              title="Report Preview"
            />
          </Box>
        </Box>
      )}

      <Dialog
        open={showInstructionsDialog}
        onClose={() => setShowInstructionsDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Modifica Report
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Inserisci le tue istruzioni per modificare il report. Sii specifico riguardo alle modifiche desiderate.
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={6}
            label="Istruzioni per la Modifica"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Es: Aggiungi più dettagli sulla dinamica dell'evento, riorganizza la sezione dei danni..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowInstructionsDialog(false)}>
            Annulla
          </Button>
          <Button
            onClick={handleRefineReport}
            variant="contained"
            disabled={!instructions.trim()}
          >
            Applica Modifiche
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default GenerateReport; 