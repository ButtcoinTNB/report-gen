import { useState, useCallback, useEffect, ChangeEvent } from 'react';
import { Container, Box, Typography, Paper, Button, TextField, Divider, Alert } from '@mui/material';
import DocumentUpload from '../components/DocumentUpload';
import AdditionalInfo from '../components/AdditionalInfo';
import ReportPreview from '../components/ReportPreview';
import LoadingIndicator from '../components/LoadingIndicator';
import { downloadApi, generateApi, editApi } from '../services';
import { AnalysisResponse, ReportPreview as ReportPreviewType } from '../types';
import { ReportPreviewCamel } from '../types/api';
import { logger } from '../utils/logger';
import { adaptReportPreview } from '../types/api';

// Define the interface matching the one in AdditionalInfo component
interface ComponentAnalysisDetails {
  valore: string;
  confidenza: 'ALTA' | 'MEDIA' | 'BASSA';
  richiede_verifica: boolean;
}

type ReportStep = 'upload' | 'additional-info' | 'preview' | 'download';

const GenerateReport: React.FC = () => {
  const [step, setStep] = useState<ReportStep>('upload');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedDocumentIds, setUploadedDocumentIds] = useState<string[]>([]);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [reportPreview, setReportPreview] = useState<ReportPreviewType | null>(null);
  const [instructions, setInstructions] = useState('');
  
  // When document IDs change, analyze them
  useEffect(() => {
    if (uploadedDocumentIds.length > 0) {
      analyzeDocuments(uploadedDocumentIds[0]);
    }
  }, [uploadedDocumentIds]);
  
  const analyzeDocuments = async (reportId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await generateApi.analyzeDocuments(reportId);
      
      logger.info('Document analysis result:', response);
      
      // Set the analysis result for the AdditionalInfo component
      setAnalysisResult(response);
      
      // Move to the next step
      setStep('additional-info');
    } catch (err) {
      logger.error('Error analyzing documents:', err);
      setError('Failed to analyze documents. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleUploadComplete = (reportId: string) => {
    setUploadedDocumentIds([reportId]);
  };
  
  const handleAdditionalInfo = async (additionalInfo: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Use the new generateReport adapter
      const response = await generateApi.generateReport(uploadedDocumentIds[0], {
        text: additionalInfo
      });
      
      // Create a ReportPreview from the camelCase response
      const preview: ReportPreviewType = {
        report_id: response.reportId,
        preview_url: response.previewUrl || '',
        status: response.status,
        message: response.message,
        // For backward compatibility
        reportId: response.reportId,
        previewUrl: response.previewUrl || ''
      };
      
      setReportPreview(preview);
      setStep('preview');
    } catch (e) {
      logger.error('Error generating report:', e);
      setError('Failed to generate report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleRefineReport = async () => {
    if (!instructions.trim() || !reportPreview?.reportId) return;
    
    setIsLoading(true);
    
    try {
      // Use the editApi adapter, which returns the response in camelCase
      const response = await editApi.editReport(reportPreview.reportId, instructions);
      
      // Create a ReportPreview from the camelCase response
      const preview: ReportPreviewType = {
        report_id: response.reportId,
        preview_url: response.previewUrl,
        status: response.status,
        message: response.message,
        // For backward compatibility
        reportId: response.reportId,
        previewUrl: response.previewUrl
      };
      
      setReportPreview(preview);
      setInstructions('');
    } catch (e) {
      logger.error('Error refining report:', e);
      setError('Failed to refine report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBack = () => {
    if (step === 'additional-info') {
      setStep('upload');
    } else if (step === 'preview') {
      setStep('additional-info');
    }
  };
  
  const handleDownload = () => {
    if (!reportPreview?.reportId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      logger.info('Downloading report with ID:', reportPreview.reportId);
      
      // Use the download URL from the preview or construct one
      const downloadUrl = reportPreview.downloadUrl || 
        downloadApi.getDownloadUrl(reportPreview.reportId);
      
      // Use the download API to trigger the download
      downloadApi.downloadToDevice(
        reportPreview.reportId, 
        `report-${reportPreview.reportId}.docx`
      );
      
      // Show a success message
      // Note: You could redirect to a success page instead
    } catch (err) {
      logger.error('Error downloading report:', err);
      setError('Failed to download report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const renderStep = () => {
    switch (step) {
      case 'upload':
        return (
          <DocumentUpload 
            onUploadComplete={handleUploadComplete}
          />
        );
      
      case 'additional-info':
        if (!analysisResult) return null;
        
        // Convert field names and data structure if needed
        return (
          <AdditionalInfo
            documentIds={uploadedDocumentIds}
            extractedVariables={analysisResult.extractedVariables}
            analysisDetails={analysisResult.analysisDetails as unknown as Record<string, ComponentAnalysisDetails>}
            fieldsNeedingAttention={analysisResult.fieldsNeedingAttention}
            onSubmit={handleAdditionalInfo}
            onBack={handleBack}
          />
        );
      
      case 'preview':
        if (!reportPreview) return null;
        
        return (
          <Box sx={{ mt: 4 }}>
            <ReportPreview
              preview={reportPreview}
              onRefine={handleRefineReport}
              onDownload={handleDownload}
              onBack={handleBack}
              instructions={instructions}
              onInstructionsChange={(e: ChangeEvent<HTMLTextAreaElement>) => setInstructions(e.target.value)}
            />
          </Box>
        );
      
      default:
        return null;
    }
  };
  
  return (
    <Container maxWidth="lg" sx={{ pb: 4 }}>
      <Box sx={{ mb: 4, mt: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Generatore di Perizie
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Carica i documenti, aggiungi informazioni e ottieni una perizia professionale in pochi minuti.
        </Typography>
      </Box>
      
      {/* Error display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {/* Loading indicator */}
      <LoadingIndicator 
        loadingState={{ 
          isLoading,
          stage: step === 'upload' ? 'uploading' : 
                 step === 'additional-info' ? 'analyzing' : 
                 step === 'preview' ? 'generating' : 'loading'
        }} 
      />
      
      {/* Current step */}
      {renderStep()}
    </Container>
  );
};

export default GenerateReport; 