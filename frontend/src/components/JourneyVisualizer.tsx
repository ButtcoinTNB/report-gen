import React from 'react';
import { 
  Box, 
  Stepper, 
  Step, 
  StepLabel, 
  StepContent, 
  Typography,
  Paper,
  useTheme
} from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import SchemaIcon from '@mui/icons-material/Schema';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import EditNoteIcon from '@mui/icons-material/EditNote';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

export type JourneyStep = {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  substeps?: { label: string; description: string; }[];
};

export interface JourneyVisualizerProps {
  activeStep: number;
  activeSubstep?: number;
  vertical?: boolean;
  showContent?: boolean;
  stepsCompleted?: string[];
  showFuture?: boolean;
}

/**
 * A component that visualizes the user's journey through the app
 * It shows the overall process flow including:
 * - File upload
 * - Information gathering
 * - Report generation
 * - Refinement options
 * - Download
 */
const JourneyVisualizer: React.FC<JourneyVisualizerProps> = ({ 
  activeStep = 0, 
  activeSubstep = 0, 
  vertical = false, 
  showContent = false,
  stepsCompleted = [],
  showFuture = true
}) => {
  const theme = useTheme();
  
  // Define the journey steps with their associated icons and descriptions
  const journeySteps: JourneyStep[] = [
    { 
      id: 'upload',
      label: "Caricamento File", 
      description: "Carica i documenti relativi al sinistro per l'analisi",
      icon: <DescriptionIcon />,
      substeps: [
        { label: "Selezione File", description: "Seleziona i documenti da analizzare" },
        { label: "Caricamento", description: "I file vengono caricati in background" }
      ]
    },
    { 
      id: 'info',
      label: "Informazioni", 
      description: "Fornisci dettagli aggiuntivi per contestualizzare il report",
      icon: <SchemaIcon />,
      substeps: [
        { label: "Dettagli", description: "Inserisci informazioni di contesto" },
        { label: "Conferma", description: "Conferma le informazioni e procedi" }
      ]
    },
    { 
      id: 'generation',
      label: "Generazione", 
      description: "L'AI analizza i documenti e genera una bozza del report",
      icon: <SmartToyIcon />,
      substeps: [
        { label: "Analisi", description: "I documenti vengono analizzati dall'AI" },
        { label: "Redazione", description: "La bozza del report viene creata" },
        { label: "Revisione", description: "L'AI rivede e migliora il testo" }
      ]
    },
    { 
      id: 'refinement',
      label: "Perfezionamento", 
      description: "Rivedi e perfeziona il report in base alle tue esigenze",
      icon: <AutoAwesomeIcon />,
      substeps: [
        { label: "Anteprima", description: "Visualizza l'anteprima del report" },
        { label: "Istruzioni", description: "Fornisci istruzioni per il perfezionamento" },
        { label: "Elaborazione", description: "L'AI perfeziona il report" }
      ]
    },
    { 
      id: 'editing',
      label: "Modifica", 
      description: "Apporta modifiche manuali al report se necessario",
      icon: <EditNoteIcon />,
      substeps: [
        { label: "Revisione", description: "Rivedi il contenuto del report" },
        { label: "Modifica", description: "Apporta modifiche manuali al testo" },
        { label: "Verifica", description: "Verifica la correttezza delle modifiche" }
      ]
    },
    { 
      id: 'download',
      label: "Download", 
      description: "Scarica il report finale in formato DOCX",
      icon: <CheckCircleIcon />,
      substeps: [
        { label: "Finalizzazione", description: "Il report viene finalizzato" },
        { label: "Download", description: "Scarica il file DOCX" }
      ]
    }
  ];
  
  // Filter steps based on showFuture
  const displaySteps = showFuture ? journeySteps : journeySteps.slice(0, activeStep + 1);
  
  return vertical ? (
    <Box sx={{ maxWidth: 400 }}>
      <Stepper activeStep={activeStep} orientation="vertical">
        {displaySteps.map((step, index) => {
          const isStepComplete = stepsCompleted.includes(step.id) || index < activeStep;
          
          return (
            <Step key={step.id} completed={isStepComplete}>
              <StepLabel 
                StepIconProps={{ 
                  icon: step.icon || (index + 1), 
                  sx: { 
                    ...(activeStep === index && {
                      color: theme.palette.secondary.main,
                    })
                  }
                }}
              >
                <Typography variant="subtitle1">{step.label}</Typography>
              </StepLabel>
              
              {showContent && (
                <StepContent>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {step.description}
                  </Typography>
                  
                  {step.substeps && activeStep === index && (
                    <Box sx={{ ml: 1 }}>
                      <Stepper activeStep={activeSubstep} orientation="vertical" sx={{ pl: 1 }}>
                        {step.substeps.map((substep, subindex) => (
                          <Step key={subindex} completed={subindex < activeSubstep}>
                            <StepLabel>
                              <Typography variant="body2">{substep.label}</Typography>
                            </StepLabel>
                            <StepContent>
                              <Typography variant="body2" color="text.secondary">
                                {substep.description}
                              </Typography>
                            </StepContent>
                          </Step>
                        ))}
                      </Stepper>
                    </Box>
                  )}
                </StepContent>
              )}
            </Step>
          );
        })}
      </Stepper>
    </Box>
  ) : (
    <Paper elevation={0} sx={{ py: 2, px: 1, bgcolor: 'transparent' }}>
      <Stepper activeStep={activeStep} alternativeLabel>
        {displaySteps.map((step, index) => {
          const isStepComplete = stepsCompleted.includes(step.id) || index < activeStep;
          
          return (
            <Step key={step.id} completed={isStepComplete}>
              <StepLabel 
                StepIconProps={{ 
                  icon: step.icon || (index + 1),
                  sx: { 
                    transition: 'transform 0.3s ease, color 0.3s ease',
                    ...(activeStep === index && {
                      transform: 'scale(1.15)',
                      color: theme.palette.secondary.main,
                    })
                  }
                }}
              >
                {step.label}
                
                {showContent && activeStep === index && (
                  <Typography variant="caption" display="block" color="text.secondary">
                    {step.description}
                  </Typography>
                )}
              </StepLabel>
            </Step>
          );
        })}
      </Stepper>
    </Paper>
  );
}

export default JourneyVisualizer; 