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

interface AnalysisDetails {
  valore: string;
  confidenza: 'ALTA' | 'MEDIA' | 'BASSA';
  richiede_verifica: boolean;
}

interface AdditionalInfoProps {
  documentIds: string[];
  extractedVariables: Record<string, string>;
  analysisDetails: Record<string, AnalysisDetails>;
  fieldsNeedingAttention: string[];
  onSubmit: (additionalInfo: string) => void;
  onBack: () => void;
}

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

const confidenceColors = {
  ALTA: 'success',
  MEDIA: 'warning',
  BASSA: 'error'
} as const;

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

  const getConfidenceIcon = (confidence: 'ALTA' | 'MEDIA' | 'BASSA') => {
    switch (confidence) {
      case 'ALTA':
        return <CheckCircleIcon color="success" />;
      case 'MEDIA':
        return <HelpOutlineIcon color="warning" />;
      case 'BASSA':
        return <ErrorOutlineIcon color="error" />;
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

          {fieldsNeedingAttention.length > 0 && (
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
                  Campi che Richiedono Attenzione ({fieldsNeedingAttention.length})
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box component="ul" sx={{ mt: 1, pl: 2 }}>
                  {fieldsNeedingAttention.map((field, index) => (
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
                {Object.entries(analysisDetails).map(([key, details]) => (
                  <Box
                    key={key}
                    sx={{
                      p: 2,
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      bgcolor: details.richiede_verifica ? 'warning.50' : 'background.paper'
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold', flex: 1 }}>
                        {fieldLabels[key] || key}
                      </Typography>
                      <Chip
                        size="small"
                        label={details.confidenza}
                        color={confidenceColors[details.confidenza]}
                        icon={getConfidenceIcon(details.confidenza)}
                      />
                    </Box>
                    <Typography variant="body2">
                      {details.valore || 'Non fornito'}
                    </Typography>
                  </Box>
                ))}
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