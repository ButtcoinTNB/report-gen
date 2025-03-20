import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  TextField,
  Typography,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { adaptApiResponse, createAnalysisResponse } from '../utils/adapters';
import { ComponentAnalysisDetails, AnalysisResponse } from '../types';
import { AnalysisDetails as ApiAnalysisDetails } from '../types/api';

const fieldLabels: Record<string, string> = {
  nome_azienda: "Nome Azienda",
  indirizzo_azienda: "Indirizzo",
  cap: "CAP",
  city: "Città",
  vs_rif: "Riferimento Cliente",
  rif_broker: "Riferimento Broker",
  polizza: "Numero Polizza",
  ns_rif: "Riferimento Interno",
  dinamica_eventi_accertamenti: "Dinamica Eventi e Accertamenti",
  foto_intervento: "Descrizione Foto Intervento",
  causa_danno: "Causa del Danno",
  item1: "Prima Voce di Danno",
  totale_item1: "Importo Primo Danno",
  item2: "Seconda Voce di Danno",
  totale_item2: "Importo Secondo Danno",
  item3: "Terza Voce di Danno",
  totale_item3: "Importo Terzo Danno",
  item4: "Quarta Voce di Danno",
  totale_item4: "Importo Quarto Danno",
  item5: "Quinta Voce di Danno",
  totale_item5: "Importo Quinto Danno",
  item6: "Sesta Voce di Danno",
  totale_item6: "Importo Sesto Danno",
  totale_danno: "Totale Danni",
  lista_allegati: "Lista Allegati"
};

// Map for confidence level display colors
const confidenceLevelColors = {
  high: 'success',
  medium: 'warning',
  low: 'error'
} as const;

/**
 * Interface for props passed to the AdditionalInfo component
 */
interface AdditionalInfoProps {
  documentIds: string[];
  extractedVariables: Record<string, string>;
  analysisDetails: Record<string, ApiAnalysisDetails>;
  fieldsNeedingAttention: string[];
  onSubmit: (additionalInfo: string) => void;
  onBack: () => void;
}

const AdditionalInfo: React.FC<AdditionalInfoProps> = ({
  documentIds,
  extractedVariables,
  analysisDetails,
  fieldsNeedingAttention,
  onSubmit,
  onBack,
}) => {
  const [additionalInfo, setAdditionalInfo] = useState('');
  const [expandedSection, setExpandedSection] = useState<string | false>('needs-attention');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(additionalInfo);
  };

  const handleAccordionChange = (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedSection(isExpanded ? panel : false);
  };

  // Create an artificial API response for our adapter function
  const apiResponse = {
    extracted_variables: analysisDetails,
    fields_needing_attention: fieldsNeedingAttention,
    status: 'success' as const,
    message: ''
  };
  
  // Use our new adapter function to get component-friendly data
  const analysisResponse = createAnalysisResponse(apiResponse);

  // Helper function to map confidence numbers to UI elements
  const getConfidenceUI = (confidence: number) => {
    if (confidence >= 0.8) {
      return { icon: <CheckCircleIcon color="success" />, label: 'High', color: 'success' as const };
    } else if (confidence >= 0.5) {
      return { icon: <HelpOutlineIcon color="warning" />, label: 'Medium', color: 'warning' as const };
    } else {
      return { icon: <ErrorOutlineIcon color="error" />, label: 'Low', color: 'error' as const };
    }
  };

  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto', mt: 4, p: 2 }}>
      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            Revisione e Informazioni Aggiuntive
          </Typography>
          
          <Typography variant="body1" sx={{ mb: 3 }}>
            L'AI ha analizzato i documenti caricati. Rivedi le informazioni estratte e aggiungi eventuali dettagli mancanti o da correggere.
          </Typography>

          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2">
              <strong>Informazione sulla privacy:</strong> Tutte le informazioni mostrate sono state estratte <strong>esclusivamente</strong> dai documenti che hai caricato.
              Il sistema non utilizza contenuti di altri documenti nel tuo report finale. I documenti caricati vengono eliminati automaticamente dopo il download del report.
            </Typography>
          </Alert>

          {analysisResponse.fieldsNeedingAttention.length > 0 && (
            <Accordion
              expanded={expandedSection === 'needs-attention'}
              onChange={handleAccordionChange('needs-attention')}
              sx={{ mb: 2 }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                sx={{ bgcolor: 'warning.light' }}
              >
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                  Campi che Richiedono Attenzione ({analysisResponse.fieldsNeedingAttention.length})
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box component="ul" sx={{ mt: 1, pl: 2 }}>
                  {analysisResponse.fieldsNeedingAttention.map((field, index) => (
                    <Typography component="li" key={index} color="text.secondary">
                      {field}
                    </Typography>
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}

          <Accordion
            expanded={expandedSection === 'all-fields'}
            onChange={handleAccordionChange('all-fields')}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                Tutte le Informazioni Estratte
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: 'grid', gap: 2 }}>
                {Object.entries(analysisResponse.analysisDetails).map(([key, details]) => {
                  const confidenceUI = getConfidenceUI(details.confidence);
                  return (
                  <Box
                    key={key}
                    sx={{
                      p: 2,
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      bgcolor: details.source === 'needs_verification' ? 'warning.50' : 'background.paper'
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold', flex: 1 }}>
                        {fieldLabels[key] || key}
                      </Typography>
                      <Chip
                        size="small"
                        label={confidenceUI.label}
                        color={confidenceUI.color}
                        icon={confidenceUI.icon}
                      />
                    </Box>
                    <Typography variant="body2">
                      {details.value || 'Non fornito'}
                    </Typography>
                  </Box>
                  );
                })}
              </Box>
            </AccordionDetails>
          </Accordion>

          <form onSubmit={handleSubmit}>
            <Box sx={{ mt: 3 }}>
              <Typography variant="h6" gutterBottom>
                Aggiungi Informazioni
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Inserisci qui le informazioni mancanti o da correggere. Specifica chiaramente il campo a cui si riferisce ogni informazione.
                Per esempio: "Il numero di polizza corretto è 12345" o "L'importo del primo danno è 1500,00 euro".
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={8}
                label="Informazioni Aggiuntive"
                value={additionalInfo}
                onChange={(e) => setAdditionalInfo(e.target.value)}
                placeholder="Inserisci qui le informazioni aggiuntive o le correzioni necessarie..."
                sx={{ mb: 3 }}
              />
            </Box>

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                onClick={onBack}
              >
                Indietro
              </Button>
              <Button
                variant="contained"
                type="submit"
                color="primary"
              >
                Genera Report
              </Button>
            </Box>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
};

export default AdditionalInfo; 