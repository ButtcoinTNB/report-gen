import React from 'react';
import { Box, Typography, Button, TextField, Paper } from '@mui/material';
import { ReportPreview as ReportPreviewType, ReportPreviewCamel } from '../types';
import { createHybridReportPreview } from '../utils/adapters';

/**
 * Props for the ReportPreview component
 * Uses the camelCase version of ReportPreview for type safety
 */
interface ReportPreviewProps {
  preview: ReportPreviewCamel;
  onRefine: () => void;
  onDownload: () => void;
  onBack: () => void;
  instructions: string;
  onInstructionsChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
}

/**
 * Component to display a preview of the generated report
 * @param preview - The report preview data in camelCase format
 * @param onRefine - Function to trigger report refinement
 * @param onDownload - Function to download the report
 * @param onBack - Function to go back to the previous step
 * @param instructions - Refinement instructions text
 * @param onInstructionsChange - Handler for instruction changes
 */
const ReportPreview: React.FC<ReportPreviewProps> = ({
  preview,
  onRefine,
  onDownload,
  onBack,
  instructions,
  onInstructionsChange
}) => {
  // Convert the camelCase preview to a hybrid format that includes both formats
  // This ensures compatibility with older code that might expect snake_case
  const hybridPreview = createHybridReportPreview(preview);

  return (
    <Paper elevation={3} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Anteprima Report
      </Typography>
      
      <Box sx={{ mb: 3 }}>
        <Typography variant="body1" paragraph>
          {preview.message}
        </Typography>
      </Box>
      
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Istruzioni per il Refinement
        </Typography>
        <TextField
          fullWidth
          multiline
          rows={4}
          value={instructions}
          onChange={onInstructionsChange}
          placeholder="Inserisci le tue istruzioni per il refinement..."
          variant="outlined"
        />
      </Box>
      
      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
        <Button onClick={onBack} variant="outlined">
          Indietro
        </Button>
        <Button onClick={onRefine} variant="contained" color="primary">
          Refine
        </Button>
        <Button onClick={onDownload} variant="contained" color="secondary">
          Scarica
        </Button>
      </Box>
    </Paper>
  );
};

export default ReportPreview; 