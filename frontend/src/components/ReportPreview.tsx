import React from 'react';
import { Box, Typography, Button, TextField, Paper } from '@mui/material';
import { ReportPreview as ReportPreviewType } from '../src/types';

interface ReportPreviewProps {
  preview: ReportPreviewType;
  onRefine: () => void;
  onDownload: () => void;
  onBack: () => void;
  instructions: string;
  onInstructionsChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
}

const ReportPreview: React.FC<ReportPreviewProps> = ({
  preview,
  onRefine,
  onDownload,
  onBack,
  instructions,
  onInstructionsChange
}) => {
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