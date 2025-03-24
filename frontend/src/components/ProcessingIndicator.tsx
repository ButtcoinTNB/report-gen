import React, { useState, useEffect, useRef } from 'react';
import { 
  Box, 
  Typography, 
  CircularProgress, 
  LinearProgress, 
  Paper, 
  Fade, 
  Grow,
  Chip,
  Stack
} from '@mui/material';
import { useTask } from '../context/TaskContext';
import { getLiveRegionProps, getProgressBarProps, generateAccessibleId } from '../utils/accessibility';

// Processing stages with descriptions
const processingStages = [
  { id: 'upload', label: 'Caricamento documenti', description: 'Stiamo caricando i tuoi documenti sul server...' },
  { id: 'extraction', label: 'Estrazione contenuto', description: 'Estraendo il testo e le informazioni dai documenti...' },
  { id: 'analysis', label: 'Analisi documenti', description: 'Analizzando le informazioni chiave nei documenti...' },
  { id: 'writer', label: 'Generazione bozza', description: 'Il nostro AI Writer sta creando la bozza del report...' },
  { id: 'reviewer', label: 'Revisione qualità', description: 'Il nostro AI Reviewer sta controllando la qualità...' },
  { id: 'refinement', label: 'Raffinamento', description: 'Ottimizzando il contenuto in base al feedback...' },
  { id: 'formatting', label: 'Formattazione', description: 'Applicando formattazione professionale al documento...' },
  { id: 'finalization', label: 'Finalizzazione', description: 'Preparando il documento finale...' }
];

// Interesting facts to display during processing
const interestingFacts = [
  "Oltre il 70% del tempo di elaborazione delle assicurazioni è dedicato alla gestione dei documenti.",
  "Un agente assicurativo trascorre in media 40 ore al mese scrivendo rapporti.",
  "L'intelligenza artificiale può ridurre i tempi di elaborazione dei report fino all'80%.",
  "La nostra AI elabora migliaia di documenti ogni giorno, migliorando continuamente.",
  "Un report generato automaticamente può avere la stessa qualità di uno scritto manualmente.",
  "Gli algoritmi di AI possono identificare modelli che potrebbero sfuggire all'occhio umano.",
  "La tecnologia che stai utilizzando analizza centinaia di variabili contemporaneamente.",
  "Gli strumenti di AI come questo stanno trasformando il settore assicurativo in tutto il mondo."
];

// Helper tips to display during processing
const helperTips = [
  "Consiglio: Più dettagliati sono i documenti caricati, migliore sarà il report generato.",
  "Suggerimento: Puoi sempre modificare il report finale se necessario.",
  "Consiglio: I report generati sono sempre conformi alle normative più recenti.",
  "Suggerimento: Salva i modelli di report che usi più frequentemente per risparmiare tempo.",
  "Consiglio: Verifica sempre i dati sensibili prima di condividere il report finale."
];

const ProcessingIndicator: React.FC = () => {
  const { activeTask } = useTask();
  const [fact, setFact] = useState<string>('');
  const [tip, setTip] = useState<string>('');
  const [showInfo, setShowInfo] = useState<boolean>(true);
  const progressId = useRef(generateAccessibleId('progress')).current;
  const statusId = useRef(generateAccessibleId('status')).current;
  
  // Current stage from task context, fallback to 'default'
  const currentStage = activeTask?.stage || 'default';
  const progress = activeTask?.progress || 0;
  const isCompleted = activeTask?.status === 'completed';
  const message = activeTask?.message;
  
  // Update facts and tips periodically to keep user engaged
  useEffect(() => {
    // Initialize with random fact and tip
    setFact(interestingFacts[Math.floor(Math.random() * interestingFacts.length)]);
    setTip(helperTips[Math.floor(Math.random() * helperTips.length)]);
    
    // Change fact every 15 seconds
    const factInterval = setInterval(() => {
      // Animate transition by hiding and showing
      setShowInfo(false);
      setTimeout(() => {
        setFact(interestingFacts[Math.floor(Math.random() * interestingFacts.length)]);
        setShowInfo(true);
      }, 500);
    }, 15000);
    
    // Change tip every 30 seconds
    const tipInterval = setInterval(() => {
      if (!showInfo) return; // Skip if we're already in transition
      
      setShowInfo(false);
      setTimeout(() => {
        setTip(helperTips[Math.floor(Math.random() * helperTips.length)]);
        setShowInfo(true);
      }, 500);
    }, 30000);
    
    return () => {
      clearInterval(factInterval);
      clearInterval(tipInterval);
    };
  }, []);
  
  // Find the current stage index
  const currentStageIndex = processingStages.findIndex(stage => stage.id === currentStage);
  
  // Current stage description for screen readers
  const currentStageDescription = processingStages[currentStageIndex]?.description || 'Elaborando il tuo report...';
  
  // Format estimated time remaining
  const formatTimeRemaining = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds} secondi`;
    } else if (seconds < 3600) {
      return `${Math.floor(seconds / 60)} minuti`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours} ore e ${minutes} minuti`;
    }
  };
  
  return (
    <Fade in={true} timeout={1000}>
      <Paper 
        elevation={3}
        sx={{
          p: 3,
          mb: 3,
          borderRadius: 2,
          boxShadow: 2,
          overflow: 'hidden',
          position: 'relative'
        }}
      >
        {/* Status text for screen readers */}
        <Box
          {...getLiveRegionProps('polite')}
          id={statusId}
          sx={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', pointerEvents: 'none', opacity: 0 }}
        >
          {isCompleted 
            ? 'Elaborazione completata!' 
            : `${currentStageDescription} Progresso al ${progress}%.`
          }
        </Box>
        
        <Fade in={true} timeout={500}>
          <Box>
            {/* Header with current stage */}
            <Typography variant="h5" gutterBottom fontWeight="bold" color="primary">
              {isCompleted ? 'Elaborazione completata!' : 'Elaborazione in corso...'}
            </Typography>
            
            <Typography variant="body1" color="text.secondary" gutterBottom>
              {isCompleted 
                ? 'Il tuo report è pronto per essere visualizzato e scaricato.' 
                : `${processingStages[currentStageIndex]?.description || 'Elaborando il tuo report...'}`
              }
            </Typography>
          </Box>
        </Fade>
        
        {/* Overall progress */}
        <Grow in={true} timeout={800}>
          <Box sx={{ mt: 3, mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Progresso totale
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {progress}%
              </Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={progress}
              id={progressId}
              {...getProgressBarProps(progress, 'Progresso elaborazione')}
              sx={{ 
                height: 10, 
                borderRadius: 5,
                '& .MuiLinearProgress-bar': {
                  borderRadius: 5,
                  background: 'linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%)',
                }
              }} 
            />
          </Box>
        </Grow>
        
        {/* Stages */}
        <Grow in={true} timeout={1000}>
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Fasi di elaborazione
            </Typography>
            
            <Stack spacing={1.5}>
              {processingStages.map((stage, index) => (
                <Box 
                  key={stage.id} 
                  sx={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between',
                    mb: 2
                  }}
                  aria-current={currentStage === stage.id ? 'step' : undefined}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box 
                      sx={{ 
                        width: 24, 
                        height: 24, 
                        borderRadius: '50%', 
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        mr: 2,
                        bgcolor: index < currentStageIndex 
                          ? 'success.main' 
                          : index === currentStageIndex 
                            ? 'primary.main' 
                            : 'grey.300',
                        transition: 'all 0.3s ease'
                      }}
                      role="presentation"
                    >
                      {index < currentStageIndex ? (
                        <Fade in={true}>
                          <Box 
                            component="span" 
                            sx={{ 
                              fontSize: 14, 
                              color: 'white',
                              fontWeight: 'bold'
                            }}
                          >
                            ✓
                          </Box>
                        </Fade>
                      ) : index === currentStageIndex ? (
                        <CircularProgress size={16} thickness={5} sx={{ color: 'white' }} />
                      ) : (
                        <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'white' }} />
                      )}
                    </Box>
                    
                    <Typography 
                      variant="body2" 
                      fontWeight={index <= currentStageIndex ? 'medium' : 'regular'}
                      color={index <= currentStageIndex ? 'text.primary' : 'text.secondary'}
                    >
                      {stage.label}
                    </Typography>
                  </Box>
                  
                  {index === currentStageIndex && !isCompleted && (
                    <Fade in={true}>
                      <Chip 
                        label="In corso" 
                        size="small" 
                        color="primary" 
                        sx={{ 
                          fontSize: '0.7rem',
                          height: 24
                        }} 
                      />
                    </Fade>
                  )}
                </Box>
              ))}
            </Stack>
          </Box>
        </Grow>
        
        {/* Estimated time and metrics */}
        <Grow in={true} timeout={1200}>
          <Box 
            sx={{ 
              display: 'flex', 
              flexWrap: 'wrap',
              gap: 2,
              mb: 3 
            }}
          >
            {estimatedTimeRemaining !== undefined && !isCompleted && (
              <Chip 
                label={`Tempo stimato: ${formatTimeRemaining(estimatedTimeRemaining)}`} 
                variant="outlined" 
                color="primary" 
              />
            )}
            
            {quality !== undefined && (
              <Chip 
                label={`Qualità: ${Math.round(quality * 100)}%`} 
                variant="outlined" 
                color={quality > 0.8 ? 'success' : quality > 0.6 ? 'primary' : 'warning'} 
              />
            )}
            
            {iterations !== undefined && (
              <Chip 
                label={`Iterazioni: ${iterations}`} 
                variant="outlined" 
                color="default" 
              />
            )}
          </Box>
        </Grow>
        
        {/* Interesting facts and tips */}
        <Fade in={showInfo} timeout={500}>
          <Box 
            sx={{ 
              bgcolor: 'info.50', 
              borderRadius: 2, 
              p: 2, 
              mt: 2,
              border: '1px solid',
              borderColor: 'info.100'
            }}
          >
            <Typography variant="body2" sx={{ mb: 1, fontStyle: 'italic' }}>
              <strong>Lo sapevi?</strong> {fact}
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              {tip}
            </Typography>
          </Box>
        </Fade>
      </Paper>
    </Fade>
  );
};

export default ProcessingIndicator; 