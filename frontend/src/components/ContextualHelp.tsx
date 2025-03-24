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
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  useTheme
} from '@mui/material';
import {
  HelpOutline as HelpIcon,
  InfoOutlined as InfoIcon,
  TipsAndUpdatesOutlined as TipsIcon,
  WarningAmberOutlined as WarningIcon,
  ArrowDropDown as ExpandIcon,
  ArrowRight as CollapseIcon,
  CheckCircleOutline as CheckIcon,
  ErrorOutline as ErrorIcon
} from '@mui/icons-material';
import { useTask, ProcessStage } from '../context/TaskContext';
import { withWindow } from '../utils/environment';

// Help content by stage
export interface HelpContent {
  title: string;
  description: string;
  tips: string[];
  warnings?: string[];
  requirements?: string[];
}

const helpContentByStage: Record<ProcessStage, HelpContent> = {
  idle: {
    title: 'Benvenuto nel Generatore di Report Assicurativi',
    description: 'Questo strumento ti aiuterà a creare report professionali da documenti assicurativi e medici.',
    tips: [
      'Puoi caricare diversi tipi di documenti: PDF, immagini, file di Word, etc.',
      'Seleziona i documenti cliccando o trascinandoli nell\'area di caricamento.'
    ]
  },
  upload: {
    title: 'Caricamento Documenti',
    description: 'Carica i documenti necessari per generare il report.',
    tips: [
      'Assicurati che i documenti siano leggibili e completi.',
      'Puoi caricare fino a 5 file contemporaneamente.',
      'Formati supportati: PDF, DOC, DOCX, JPG, PNG'
    ],
    warnings: [
      'I file non devono superare i 10MB ciascuno.',
      'Documenti protetti da password non possono essere elaborati.'
    ],
    requirements: [
      'È necessario caricare almeno un documento per procedere.'
    ]
  },
  extraction: {
    title: 'Estrazione del Contenuto',
    description: 'Stiamo estraendo le informazioni dai documenti caricati...',
    tips: [
      'Questo processo è automatico e può richiedere alcuni minuti.',
      'La durata dipende dalla complessità e dal numero dei documenti.'
    ]
  },
  analysis: {
    title: 'Analisi dei Dati',
    description: 'Stiamo analizzando le informazioni estratte per identificare le sezioni chiave per il report.',
    tips: [
      'Vengono riconosciuti automaticamente i dati fondamentali come sinistri, clausole, coperture.',
      'Il sistema identifica anche le relazioni tra i diversi documenti.'
    ]
  },
  writer: {
    title: 'Generazione della Bozza',
    description: 'L\'intelligenza artificiale sta generando una bozza del report con tutte le informazioni rilevanti.',
    tips: [
      'La bozza seguirà la struttura standard dei report assicurativi.',
      'Vengono inclusi solo i dati pertinenti per il report finale.'
    ]
  },
  reviewer: {
    title: 'Revisione della Bozza',
    description: 'Il sistema sta revisionando la bozza per verificarne la completezza e la correttezza.',
    tips: [
      'Questa fase migliora la qualità del report finale.',
      'Vengono verificati il formato, il tono e la precisione dei dati.'
    ]
  },
  refinement: {
    title: 'Miglioramento del Report',
    description: 'Ora puoi fornire istruzioni per migliorare il report generato.',
    tips: [
      'Inserisci istruzioni specifiche come "Aggiungi più dettagli sulla clausola X" o "Riorganizza la sezione Y".',
      'Puoi richiedere modifiche multiple in un\'unica istruzione.',
      'L\'AI cercherà di applicare tutte le modifiche richieste mantenendo la coerenza del documento.'
    ],
    requirements: [
      'Inserisci istruzioni chiare e specifiche per ottenere i migliori risultati.'
    ]
  },
  formatting: {
    title: 'Formattazione del Report',
    description: 'Stiamo applicando la formattazione finale al report per renderlo professionale e pronto all\'uso.',
    tips: [
      'Viene applicato lo stile standard per i report assicurativi.',
      'Vengono formattati correttamente intestazioni, tabelle e riferimenti.'
    ]
  },
  finalization: {
    title: 'Report Pronto',
    description: 'Il tuo report è pronto per essere scaricato e utilizzato.',
    tips: [
      'Puoi scaricare il report in formato DOCX o PDF.',
      'Il report è modificabile se scaricato in formato DOCX.'
    ]
  }
};

interface ContextualHelpProps {
  stage?: ProcessStage;
  content?: HelpContent;
  autoCollapse?: boolean;
}

export const ContextualHelp: React.FC<ContextualHelpProps> = ({
  stage: propStage,
  content: propContent,
  autoCollapse = true
}) => {
  const theme = useTheme();
  const { task } = useTask();
  const [expanded, setExpanded] = useState(!autoCollapse);
  const [currentStage, setCurrentStage] = useState<ProcessStage>(propStage || task.stage);
  
  // Use provided content or get content based on current stage
  const content = propContent || helpContentByStage[currentStage];
  
  // Update when task stage changes
  useEffect(() => {
    if (!propStage && task.stage !== currentStage) {
      setCurrentStage(task.stage);
      
      // Auto-expand when stage changes
      if (autoCollapse) {
        setExpanded(true);
        
        // Auto-collapse after 10 seconds
        const timer = setTimeout(() => {
          setExpanded(false);
        }, 10000);
        
        return () => clearTimeout(timer);
      }
    }
  }, [task.stage, currentStage, propStage, autoCollapse]);
  
  return (
    <Paper 
      elevation={2} 
      sx={{ 
        p: 2, 
        position: 'relative',
        mb: 3,
        bgcolor: theme.palette.background.paper,
        borderLeft: `4px solid ${theme.palette.primary.main}`
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <HelpIcon color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6">{content.title}</Typography>
        </Box>
        <IconButton onClick={() => setExpanded(!expanded)} size="small">
          {expanded ? <ExpandIcon /> : <CollapseIcon />}
        </IconButton>
      </Box>
      
      <Collapse in={expanded}>
        <Box sx={{ mt: 2 }}>
          <Typography variant="body1" paragraph>
            {content.description}
          </Typography>
          
          {content.tips.length > 0 && (
            <>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <TipsIcon fontSize="small" color="primary" sx={{ mr: 0.5 }} />
                <Typography variant="subtitle2">Suggerimenti</Typography>
              </Box>
              <List dense disablePadding sx={{ mb: 2 }}>
                {content.tips.map((tip, index) => (
                  <ListItem key={index} disableGutters sx={{ py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <CheckIcon fontSize="small" color="success" />
                    </ListItemIcon>
                    <ListItemText primary={tip} />
                  </ListItem>
                ))}
              </List>
            </>
          )}
          
          {content.warnings && content.warnings.length > 0 && (
            <>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <WarningIcon fontSize="small" color="warning" sx={{ mr: 0.5 }} />
                <Typography variant="subtitle2">Avvertenze</Typography>
              </Box>
              <List dense disablePadding sx={{ mb: 2 }}>
                {content.warnings.map((warning, index) => (
                  <ListItem key={index} disableGutters sx={{ py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <WarningIcon fontSize="small" color="warning" />
                    </ListItemIcon>
                    <ListItemText primary={warning} />
                  </ListItem>
                ))}
              </List>
            </>
          )}
          
          {content.requirements && content.requirements.length > 0 && (
            <>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <InfoIcon fontSize="small" color="info" sx={{ mr: 0.5 }} />
                <Typography variant="subtitle2">Requisiti</Typography>
              </Box>
              <List dense disablePadding>
                {content.requirements.map((requirement, index) => (
                  <ListItem key={index} disableGutters sx={{ py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <ErrorIcon fontSize="small" color="info" />
                    </ListItemIcon>
                    <ListItemText primary={requirement} />
                  </ListItem>
                ))}
              </List>
            </>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default ContextualHelp; 