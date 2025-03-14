'use client';

import React, { useState } from 'react';
import { Container, Box, Typography, Stepper, Step, StepLabel } from '@mui/material';
import Navbar from '@/components/Navbar';
import FileUpload from '@/components/FileUpload';
import ReportGenerator from '@/components/ReportGenerator';
import ReportPreview from '@/components/ReportPreview';
import DownloadReport from '@/components/DownloadReport';

export default function Home() {
  const [reportId, setReportId] = useState<number | null>(null);
  const [generatedText, setGeneratedText] = useState<string | null>(null);
  const [isPdfReady, setIsPdfReady] = useState<boolean>(false);
  const [activeStep, setActiveStep] = useState<number>(0);

  // Step labels
  const steps = ['Upload Documents', 'Generate Report', 'Edit & Preview', 'Download'];

  // Handlers for various stages of the process
  const handleUploadSuccess = (id: number) => {
    setReportId(id);
    setActiveStep(1); // Move to generate step
  };

  const handleGenerateSuccess = (text: string) => {
    setGeneratedText(text);
    setActiveStep(2); // Move to edit & preview step
  };

  const handleReportUpdated = (text: string) => {
    setGeneratedText(text);
  };

  const handlePreviewReady = () => {
    setIsPdfReady(true);
    setActiveStep(3); // Move to download step
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

        <Box>
          {/* Step 1: Upload */}
          <FileUpload onUploadSuccess={handleUploadSuccess} />

          {/* Step 2: Generate */}
          {reportId && (
            <ReportGenerator 
              reportId={reportId}
              onGenerateSuccess={handleGenerateSuccess}
            />
          )}

          {/* Step 3: Edit & Preview */}
          {generatedText && (
            <ReportPreview
              reportId={reportId}
              reportText={generatedText}
              onReportUpdated={handleReportUpdated}
              onPreviewReady={handlePreviewReady}
            />
          )}

          {/* Step 4: Download */}
          {generatedText && (
            <DownloadReport 
              reportId={reportId}
              isPdfReady={isPdfReady}
            />
          )}
        </Box>
      </Container>
    </>
  );
}
