import React from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Divider, 
  LinearProgress, 
  Tooltip,
  Grid,
  CardContent,
  Card
} from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import EditIcon from '@mui/icons-material/Edit';
import GradeIcon from '@mui/icons-material/Grade';
import VerifiedIcon from '@mui/icons-material/Verified';

interface ReportSummaryProps {
  timeEstimate?: number; // Time saved in minutes
  editCount?: number; // Number of manual edits
  qualityScore?: number; // Quality score out of 100
  iterations?: number; // Number of AI refinement iterations
}

/**
 * Report Summary component that displays metrics about the generated report
 * This is shown before the final download to give users feedback on the value provided
 */
const ReportSummary: React.FC<ReportSummaryProps> = ({
  timeEstimate = 120, // Default 2 hours
  editCount = 0,
  qualityScore = 90,
  iterations = 0
}) => {
  // Format time saved in a human-readable format
  const formatTimeSaved = (minutes: number): string => {
    if (minutes < 60) {
      return `${minutes} minuti`;
    }
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    
    if (remainingMinutes === 0) {
      return hours === 1 ? `1 ora` : `${hours} ore`;
    }
    
    return hours === 1 
      ? `1 ora e ${remainingMinutes} minuti` 
      : `${hours} ore e ${remainingMinutes} minuti`;
  };

  return (
    <Paper elevation={3} sx={{ p: 3, my: 3, borderRadius: 2, bgcolor: 'background.paper' }}>
      <Box sx={{ textAlign: 'center', mb: 3 }}>
        <Typography variant="h5" component="h2" gutterBottom fontWeight="bold">
          Riepilogo Report
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Hai creato un report assicurativo professionale — 10 volte più velocemente.
        </Typography>
        <Typography variant="body2" color="primary" fontWeight="medium" sx={{ mt: 1 }}>
          Pronto per il prossimo?
        </Typography>
      </Box>
      
      <Divider sx={{ my: 2 }} />
      
      <Grid container spacing={3} sx={{ mt: 1 }}>
        {/* Time Saved Metric */}
        <Grid item xs={12} sm={6} md={3}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <AccessTimeIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle1" fontWeight="medium">
                  Tempo Risparmiato
                </Typography>
              </Box>
              <Typography variant="h6" color="primary.main" fontWeight="bold">
                {formatTimeSaved(timeEstimate)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                rispetto alla creazione manuale
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Manual Edits Metric */}
        <Grid item xs={12} sm={6} md={3}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <EditIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle1" fontWeight="medium">
                  Modifiche Manuali
                </Typography>
              </Box>
              <Typography variant="h6" color="primary.main" fontWeight="bold">
                {editCount}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                perfezionamenti applicati
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Quality Score Metric */}
        <Grid item xs={12} sm={6} md={3}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <GradeIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle1" fontWeight="medium">
                  Punteggio Qualità
                </Typography>
              </Box>
              <Box display="flex" alignItems="center">
                <Typography variant="h6" color="primary.main" fontWeight="bold" sx={{ mr: 1 }}>
                  {qualityScore}/100
                </Typography>
              </Box>
              <Box sx={{ mt: 1, mb: 1 }}>
                <LinearProgress 
                  variant="determinate" 
                  value={qualityScore} 
                  sx={{
                    height: 8,
                    borderRadius: 5,
                    backgroundColor: 'grey.200',
                    '& .MuiLinearProgress-bar': {
                      borderRadius: 5,
                      backgroundColor: qualityScore > 85 ? 'success.main' :
                                      qualityScore > 70 ? 'warning.main' : 'error.main'
                    }
                  }}
                />
              </Box>
              <Typography variant="caption" color="text.secondary">
                valutato dal nostro sistema AI
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        {/* AI Refinements Metric */}
        <Grid item xs={12} sm={6} md={3}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <VerifiedIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle1" fontWeight="medium">
                  Iterazioni AI
                </Typography>
              </Box>
              <Typography variant="h6" color="primary.main" fontWeight="bold">
                {iterations}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                cicli di perfezionamento automatico
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default ReportSummary; 