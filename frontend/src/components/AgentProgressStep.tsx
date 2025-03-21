"use client";

import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Psychology as WriterIcon,
  RateReview as ReviewerIcon,
  CheckCircle as DoneIcon,
  Info as InfoIcon
} from '@mui/icons-material';

interface AgentProgressStepProps {
  step: "writer" | "reviewer";
  loop: number;
  totalLoops: number;
  feedback?: { score: number; suggestions: string[] };
  isFinal: boolean;
}

export function AgentProgressStep({ step, loop, totalLoops, feedback, isFinal }: AgentProgressStepProps) {
  const progress = (loop / totalLoops) * 100;

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle1" sx={{ flex: 1 }}>
          Iterazione {loop} di {totalLoops}
        </Typography>
        <Chip
          label={`${Math.round(progress)}%`}
          color="primary"
          size="small"
          sx={{ ml: 1 }}
        />
      </Box>

      <LinearProgress 
        variant="determinate" 
        value={progress} 
        sx={{ mb: 3, height: 8, borderRadius: 1 }}
      />

      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        {step === "writer" ? (
          <>
            <WriterIcon color="primary" sx={{ mr: 1 }} />
            <Typography color="primary">
              Il primo agente sta generando una nuova versione del report...
            </Typography>
          </>
        ) : (
          <>
            <ReviewerIcon color="warning" sx={{ mr: 1 }} />
            <Typography color="warning.main">
              Il secondo agente sta analizzando il report per coerenza, formato e stile...
            </Typography>
          </>
        )}
      </Box>

      {isFinal && (
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          mt: 2, 
          p: 2, 
          bgcolor: 'success.light',
          borderRadius: 1
        }}>
          <DoneIcon color="success" sx={{ mr: 1 }} />
          <Typography color="success.dark" fontWeight="medium">
            Il report è pronto! Puoi modificarlo o scaricarlo.
          </Typography>
        </Box>
      )}

      {feedback?.suggestions?.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Suggerimenti del revisore:
          </Typography>
          <List dense>
            {feedback.suggestions.map((suggestion, i) => (
              <ListItem key={i}>
                <ListItemIcon>
                  <InfoIcon fontSize="small" color="info" />
                </ListItemIcon>
                <ListItemText 
                  primary={suggestion}
                  primaryTypographyProps={{
                    variant: 'body2',
                    color: 'text.secondary'
                  }}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Paper>
  );
} 