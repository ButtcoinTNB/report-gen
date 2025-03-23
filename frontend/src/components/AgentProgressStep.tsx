"use client";

import React from 'react';
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
  Fade,
  Slide,
  Tooltip,
} from '@mui/material';
import {
  Psychology as WriterIcon,
  RateReview as ReviewerIcon,
  CheckCircle as DoneIcon,
  Info as InfoIcon,
  Timer as TimeIcon,
  ReportProblem as ProblemIcon
} from '@mui/icons-material';

interface AgentProgressStepProps {
  step: "writer" | "reviewer";
  loop: number;
  totalLoops: number;
  feedback?: { score: number; suggestions: string[] };
  isFinal: boolean;
  estimatedTimeRemaining?: number | null;
  isStalled?: boolean;
}

export function AgentProgressStep({ 
  step, 
  loop, 
  totalLoops, 
  feedback, 
  isFinal,
  estimatedTimeRemaining,
  isStalled = false
}: AgentProgressStepProps) {
  const progress = (loop / totalLoops) * 100;

  // Format estimated time remaining
  const formatEstimatedTime = () => {
    if (!estimatedTimeRemaining) return 'Calcolo in corso...';
    
    const minutes = Math.floor(estimatedTimeRemaining / 60);
    const seconds = Math.round(estimatedTimeRemaining % 60);
    
    if (minutes > 0) {
      return `${minutes} min ${seconds} sec`;
    }
    
    return `${seconds} secondi`;
  };

  return (
    <Fade in={true} timeout={500}>
      <Paper 
        elevation={2} 
        sx={{ 
          p: 3, 
          mb: 3, 
          borderRadius: 2,
          transition: 'all 0.3s ease',
          border: isStalled ? '1px solid #f4d35e' : 'none',
          bgcolor: isStalled ? 'rgba(244, 211, 94, 0.05)' : 'background.paper'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, justifyContent: 'space-between' }}>
          <Typography variant="subtitle1" sx={{ flex: 1 }}>
            Iterazione {loop} di {totalLoops}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {estimatedTimeRemaining !== undefined && (
              <Tooltip title="Tempo stimato rimanente">
                <Chip
                  icon={<TimeIcon fontSize="small" />}
                  label={formatEstimatedTime()}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
              </Tooltip>
            )}
            
            <Chip
              label={`${Math.round(progress)}%`}
              color="primary"
              size="small"
            />
          </Box>
        </Box>

        <LinearProgress 
          variant="determinate" 
          value={progress} 
          sx={{ 
            mb: 3, 
            height: 8, 
            borderRadius: 1,
            '.MuiLinearProgress-bar': {
              transition: 'transform 1s ease'
            }
          }}
        />

        <Slide in={true} direction="right" timeout={300}>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            mb: 2,
            p: 1.5,
            borderRadius: 1,
            bgcolor: step === "writer" ? 'primary.lighter' : 'warning.lighter'
          }}>
            {step === "writer" ? (
              <>
                <WriterIcon color="primary" sx={{ mr: 1 }} />
                <Typography color="primary.main" fontWeight="medium">
                  Il primo agente sta generando una nuova versione del report...
                </Typography>
              </>
            ) : (
              <>
                <ReviewerIcon color="warning" sx={{ mr: 1 }} />
                <Typography color="warning.main" fontWeight="medium">
                  Il secondo agente sta analizzando il report per coerenza, formato e stile...
                </Typography>
              </>
            )}
          </Box>
        </Slide>

        {/* Stalled warning */}
        {isStalled && (
          <Fade in={true} timeout={800}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              mb: 2, 
              p: 1.5, 
              bgcolor: 'warning.lighter',
              borderRadius: 1
            }}>
              <ProblemIcon color="warning" sx={{ mr: 1 }} />
              <Typography color="warning.main" fontWeight="medium">
                L'elaborazione sta richiedendo più tempo del previsto. Si prega di attendere...
              </Typography>
            </Box>
          </Fade>
        )}

        {isFinal && (
          <Fade in={true} timeout={800}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              mt: 2, 
              p: 2, 
              bgcolor: 'success.lighter',
              borderRadius: 1
            }}>
              <DoneIcon color="success" sx={{ mr: 1 }} />
              <Typography color="success.dark" fontWeight="medium">
                Il report è pronto! Puoi modificarlo o scaricarlo.
              </Typography>
            </Box>
          </Fade>
        )}

        {feedback?.suggestions?.length > 0 && (
          <Fade in={true} timeout={600}>
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
          </Fade>
        )}
      </Paper>
    </Fade>
  );
} 