import { useState, useCallback, useEffect, ChangeEvent, FormEvent } from 'react';
import { Container, Box, Typography, Paper, Button, TextField, Divider, Alert } from '@mui/material';
import DocumentUpload from '../components/DocumentUpload';
import AdditionalInfo from '../components/AdditionalInfo';
import LoadingIndicator from '../components/LoadingIndicator';
import { AgentLoopRunner } from '../components/AgentLoopRunner';
import { DocxPreviewEditor } from '../components/DocxPreviewEditor';
import { downloadApi, generateApi, editApi } from '../services';
import { 
  AnalysisResponse, 
  ReportPreviewCamel 
} from '../types';
import { logger } from '../utils/logger';
import { adaptApiResponse, createHybridReportPreview } from '../utils/adapters';
import { AnalysisDetails } from '../types/api';
import { GenerateReportRequest } from '../services/api/ReportService';

type ReportStep = 'upload' | 'additional-info' | 'preview' | 'download';

/**
 * Generate Report page component
 * Handles the multi-step process of generating a report
 */
const GenerateReport: React.FC = () => {
  const [step, setStep] = useState<ReportStep>('upload');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedDocumentIds, setUploadedDocumentIds] = useState<string[]>([]);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [reportPreview, setReportPreview] = useState<ReportPreviewCamel | null>(null);
  const [instructions, setInstructions] = useState<string>('');
  
  // When document IDs change, analyze them
  useEffect(() => {
    if (uploadedDocumentIds.length > 0) {
      analyzeDocuments(uploadedDocumentIds[0]);
    }
  }, [uploadedDocumentIds]);
  
  /**
   * Analyze documents with the given report ID
   * @param reportId - The ID of the report to analyze
   */
  const analyzeDocuments = async (reportId: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await generateApi.analyzeDocuments(reportId);
      
      logger.info('Document analysis result:', response);
      
      // Set the analysis result for the AdditionalInfo component
      setAnalysisResult(response);
      
      // Move to the next step
      setStep('additional-info');
    } catch (err: any) {
      logger.error('Error analyzing documents:', err);
      setError('Failed to analyze documents. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  /**
   * Handle the upload complete event
   * @param reportId - The ID of the newly created report
   */
  const handleUploadComplete = useCallback((reportId: string): void => {
    setUploadedDocumentIds([reportId]);
  }, []);
  
  /**
   * Handle the additional info submission
   * @param additionalInfo - The additional info text entered by the user
   */
  const handleAdditionalInfo = async (additionalInfo: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Create a proper request object
      const requestData: GenerateReportRequest = {
        text: additionalInfo
      };
      
      // Use the proper generateReport adapter
      const response = await generateApi.generateReport(uploadedDocumentIds[0], requestData);
      
      // Ensure previewUrl is always a string
      const preview: ReportPreviewCamel = {
        ...response,
        previewUrl: response.previewUrl || '' // Ensure it's never undefined
      };
      
      setReportPreview(preview);
      setStep('preview');
    } catch (err: any) {
      logger.error('Error generating report:', err);
      setError('Failed to generate report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  /**
   * Handle report refinement based on user instructions
   */
  const handleRefineReport = async (): Promise<void> => {
    if (!instructions.trim() || !reportPreview?.reportId) return;
    
    setIsLoading(true);
    
    try {
      // Use the editApi adapter, which returns the response in camelCase
      const response = await editApi.editReport(reportPreview.reportId, instructions);
      
      // Ensure previewUrl is always a string
      const preview: ReportPreviewCamel = {
        ...response,
        previewUrl: response.previewUrl || '' // Ensure it's never undefined
      };
      
      setReportPreview(preview);
      setInstructions('');
    } catch (err: any) {
      logger.error('Error refining report:', err);
      setError('Failed to refine report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle navigation back to the previous step
   */
  const handleBack = useCallback((): void => {
    if (step === 'additional-info') {
      setStep('upload');
    } else if (step === 'preview') {
      setStep('additional-info');
    }
  }, [step]);
  
  /**
   * Handle the report download action
   */
  const handleDownload = useCallback((): void => {
    if (!reportPreview?.reportId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      logger.info('Downloading report with ID:', reportPreview.reportId);
      
      // Construct the download URL
      const downloadUrl = downloadApi.getDownloadUrl(reportPreview.reportId);
      
      // Use the download API to trigger the download
      downloadApi.downloadToDevice(
        reportPreview.reportId, 
        `report-${reportPreview.reportId}.docx`
      );
      
      // Show a success message
      // Note: You could redirect to a success page instead
    } catch (err: any) {
      logger.error('Error downloading report:', err);
      setError('Failed to download report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [reportPreview]);
  
  /**
   * Handle changes to the instructions text field
   * @param e - The change event from the text area
   */
  const handleInstructionsChange = useCallback((e: ChangeEvent<HTMLTextAreaElement>): void => {
    setInstructions(e.target.value);
  }, []);
  
  /**
   * Render the appropriate step component based on current state
   */
  const renderStep = useCallback(() => {
    switch (step) {
      case 'upload':
        return (
          <DocumentUpload 
            onUploadComplete={handleUploadComplete}
          />
        );
      
      case 'additional-info':
        if (!analysisResult) return null;
        
        return (
          <AdditionalInfo
            documentIds={uploadedDocumentIds}
            extractedVariables={analysisResult.extractedVariables}
            analysisDetails={analysisResult.analysisDetails as unknown as Record<string, AnalysisDetails>}
            fieldsNeedingAttention={analysisResult.fieldsNeedingAttention}
            onSubmit={handleAdditionalInfo}
            onBack={handleBack}
          />
        );
      
      case 'preview':
        if (!reportPreview) return null;
        
        return (
          <Box sx={{ mt: 4 }}>
            <Button
              variant="contained"
              color="primary"
              onClick={() => handleAdditionalInfo("")}
              sx={{ mb: 2 }}
            >
              Genera Report AI
            </Button>
            <AgentLoopRunner 
              reportId={uploadedDocumentIds[0]}
              onComplete={(result) => {
                if (result.previewUrl) {
                  setReportPreview({
                    ...reportPreview,
                    previewUrl: result.previewUrl
                  });
                }
              }}
            />
          </Box>
        );
      
      default:
        return null;
    }
  }, [
    step, 
    analysisResult, 
    reportPreview, 
    uploadedDocumentIds, 
    handleUploadComplete, 
    handleAdditionalInfo, 
    handleBack, 
    handleRefineReport, 
    handleDownload, 
    instructions, 
    handleInstructionsChange
  ]);
  
  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4, mb: 8 }}>
        <Typography variant="h4" gutterBottom align="center">
          Generazione Report Assicurativo
        </Typography>
        
        <Typography variant="body1" paragraph align="center" sx={{ mb: 6 }}>
          {step === 'upload' && 'Carica i documenti per iniziare la generazione del report.'}
          {step === 'additional-info' && 'Fornisci informazioni aggiuntive per migliorare il report.'}
          {step === 'preview' && 'Anteprima del report generato dall\'AI.'}
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 4 }}>
            {error}
          </Alert>
        )}

        {isLoading ? (
          <LoadingIndicator 
            loadingState={{
              isLoading: true,
              stage: step === 'upload' ? 'uploading' : step === 'additional-info' ? 'analyzing' : 'generating'
            }}
          />
        ) : (
          renderStep()
        )}
      </Box>
    </Container>
  );
};

export default GenerateReport; 