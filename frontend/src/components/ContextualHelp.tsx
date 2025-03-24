import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Fade, 
  Paper, 
  IconButton, 
  Collapse,
  Alert,
  Divider,
  Link,
  Tooltip
} from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import CloseIcon from '@mui/icons-material/Close';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import InfoIcon from '@mui/icons-material/Info';
import { useTask } from '../context/TaskContext';

// Define help content by processing stage
const helpContent: Record<string, {
  title: string;
  description: string;
  tips: string[];
  actions?: Array<{
    label: string;
    description: string;
  }>;
}> = {
  // Stage-specific help
  'upload': {
    title: 'Caricamento Documenti',
    description: 'In questa fase, i tuoi documenti vengono caricati sul server per l\'elaborazione.',
    tips: [
      'I formati supportati includono PDF, DOCX, XLSX e JPG/PNG.',
      'I documenti più grandi possono richiedere più tempo per il caricamento.',
      'Assicurati che i file non siano danneggiati o protetti da password.'
    ],
    actions: [
      { label: 'Annulla', description: 'Puoi annullare il caricamento in qualsiasi momento cliccando su "Annulla".' }
    ]
  },
  'extraction': {
    title: 'Estrazione Contenuto',
    description: 'Il sistema sta analizzando i documenti per estrarre testo, tabelle e altri dati rilevanti.',
    tips: [
      'I documenti scansionati richiedono OCR, che potrebbe richiedere più tempo.',
      'I documenti ben formattati producono risultati migliori.',
      'Le tabelle e i moduli vengono analizzati automaticamente.'
    ]
  },
  'analysis': {
    title: 'Analisi Documenti',
    description: 'Il sistema sta identificando informazioni chiave nei documenti come clausole, dettagli della polizza e dati del cliente.',
    tips: [
      'Questa fase è ottimizzata per l\'identificazione di termini assicurativi.',
      'L\'intelligenza artificiale riconosce pattern comuni nei documenti assicurativi.',
      'Le relazioni tra diversi documenti vengono analizzate per coerenza.'
    ]
  },
  'writer': {
    title: 'Generazione Bozza',
    description: 'L\'AI Writer sta creando una bozza professionale del report basata sui documenti analizzati.',
    tips: [
      'La bozza segue standard e best practices del settore assicurativo.',
      'Il contenuto viene strutturato in sezioni logiche per facilità di lettura.',
      'Vengono generate spiegazioni per termini tecnici e clausole complesse.'
    ],
    actions: [
      { label: 'Visualizza anteprima', description: 'Quando disponibile, potrai vedere l\'anteprima della bozza in tempo reale.' }
    ]
  },
  'reviewer': {
    title: 'Revisione Qualità',
    description: 'L\'AI Reviewer sta valutando la qualità e la completezza della bozza generata.',
    tips: [
      'Il reviewer verifica che tutte le informazioni chiave siano incluse.',
      'Controlla la correttezza delle informazioni rispetto ai documenti originali.',
      'Valuta la chiarezza e la professionalità del linguaggio utilizzato.'
    ]
  },
  'refinement': {
    title: 'Raffinamento',
    description: 'La bozza viene ottimizzata in base al feedback del Reviewer per migliorarne la qualità.',
    tips: [
      'Questa fase può richiedere più iterazioni per documenti complessi.',
      'Ogni iterazione migliora la qualità complessiva del report.',
      'Il sistema applica automaticamente correzioni e miglioramenti.'
    ]
  },
  'formatting': {
    title: 'Formattazione',
    description: 'Il sistema sta applicando una formattazione professionale al documento.',
    tips: [
      'Vengono applicati stili e intestazioni consistenti.',
      'Le tabelle e i grafici vengono formattati per massima leggibilità.',
      'Il documento segue standard professionali di layout.'
    ]
  },
  'finalization': {
    title: 'Finalizzazione',
    description: 'Il documento finale viene preparato per la consegna.',
    tips: [
      'Viene creato un indice e una struttura di navigazione.',
      'I metadati del documento vengono aggiornati con informazioni rilevanti.',
      'Il documento viene ottimizzato per la stampa e la visualizzazione digitale.'
    ],
    actions: [
      { label: 'Anteprima', description: 'Puoi visualizzare un\'anteprima del documento finale prima di scaricarlo.' },
      { label: 'Download', description: 'Quando pronto, potrai scaricare il documento in formato DOCX o PDF.' }
    ]
  },
  // Default help for unknown stages
  'default': {
    title: 'Elaborazione in Corso',
    description: 'Il sistema sta elaborando i tuoi documenti per generare un report professionale.',
    tips: [
      'Il tempo di elaborazione dipende dalla complessità e dal numero di documenti.',
      'Potrai visualizzare e modificare il report una volta completato il processo.',
      'Il sistema applica automaticamente best practices del settore assicurativo.'
    ]
  }
};

// Main component
const ContextualHelp: React.FC = () => {
  const [expanded, setExpanded] = useState<boolean>(false);
  const [lastStage, setLastStage] = useState<string>('default');
  const [showHint, setShowHint] = useState<boolean>(false);
  const { activeTask } = useTask();
  
  // Get current stage or default
  const currentStage = activeTask?.stage || 'default';
  
  // Show hint after 10 seconds of inactivity in a new stage
  useEffect(() => {
    if (currentStage !== lastStage) {
      setLastStage(currentStage);
      setShowHint(false);
      
      const timer = setTimeout(() => {
        if (!expanded) {
          setShowHint(true);
        }
      }, 10000);
      
      return () => clearTimeout(timer);
    }
  }, [currentStage, lastStage, expanded]);
  
  // Hide hint when help is expanded
  useEffect(() => {
    if (expanded) {
      setShowHint(false);
    }
  }, [expanded]);
  
  // Get help content for current stage
  const help = helpContent[currentStage] || helpContent.default;
  
  return (
    <Box sx={{ position: 'relative', mb: 3 }}>
      {/* Help button */}
      <Box sx={{ position: 'absolute', top: -10, right: 10, zIndex: 10 }}>
        <Tooltip title={expanded ? "Chiudi guida" : "Mostra guida"}>
          <IconButton 
            onClick={() => setExpanded(!expanded)}
            color="primary"
            sx={{ 
              bgcolor: 'background.paper',
              boxShadow: 1,
              '&:hover': {
                bgcolor: 'primary.50'
              }
            }}
          >
            {expanded ? <CloseIcon /> : <HelpOutlineIcon />}
          </IconButton>
        </Tooltip>
      </Box>
      
      {/* Hint notification */}
      <Fade in={showHint} timeout={500}>
        <Alert 
          severity="info" 
          icon={<LightbulbIcon />}
          sx={{ 
            position: 'absolute', 
            top: -15, 
            right: 60,
            maxWidth: 250,
            boxShadow: 2,
            zIndex: 5
          }}
          onClose={() => setShowHint(false)}
        >
          Hai bisogno di aiuto con la fase di <strong>{help.title.toLowerCase()}</strong>?
        </Alert>
      </Fade>
      
      {/* Main help content */}
      <Collapse in={expanded} timeout={300}>
        <Paper
          elevation={3}
          sx={{
            p: 3,
            mt: 2,
            borderRadius: 2,
            borderLeft: '4px solid',
            borderColor: 'primary.main'
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <InfoIcon color="primary" sx={{ mr: 1 }} />
            <Typography variant="h6" color="primary" fontWeight="medium">
              {help.title}
            </Typography>
          </Box>
          
          <Typography variant="body1" paragraph>
            {help.description}
          </Typography>
          
          <Divider sx={{ my: 2 }} />
          
          <Typography variant="subtitle2" gutterBottom color="text.secondary">
            Suggerimenti utili:
          </Typography>
          
          <Box component="ul" sx={{ pl: 2, mt: 1 }}>
            {help.tips.map((tip, index) => (
              <Typography component="li" variant="body2" key={index} sx={{ mb: 1 }}>
                {tip}
              </Typography>
            ))}
          </Box>
          
          {help.actions && help.actions.length > 0 && (
            <>
              <Divider sx={{ my: 2 }} />
              
              <Typography variant="subtitle2" gutterBottom color="text.secondary">
                Azioni disponibili:
              </Typography>
              
              <Box sx={{ mt: 1 }}>
                {help.actions.map((action, index) => (
                  <Box key={index} sx={{ mb: 1 }}>
                    <Typography variant="body2" fontWeight="medium">
                      {action.label}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {action.description}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </>
          )}
          
          <Divider sx={{ my: 2 }} />
          
          <Typography variant="body2" color="text.secondary">
            Hai bisogno di ulteriore assistenza? <Link href="#" underline="hover">Consulta la guida completa</Link> o <Link href="#" underline="hover">contatta il supporto</Link>.
          </Typography>
        </Paper>
      </Collapse>
    </Box>
  );
};

export default ContextualHelp; 