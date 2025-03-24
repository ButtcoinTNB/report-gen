import React, { useState } from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Paper,
  Divider,
  Chip,
  Tooltip,
  useTheme,
  Collapse,
  Button
} from '@mui/material';
import {
  History as HistoryIcon,
  RestoreOutlined as RestoreIcon,
  ArrowDropDown as ExpandIcon,
  ArrowRight as CollapseIcon,
  VisibilityOutlined as ViewIcon,
  CompareArrowsOutlined as CompareIcon,
  CheckCircleOutline as CurrentIcon,
  DownloadOutlined as DownloadIcon
} from '@mui/icons-material';
import { useTask } from '../context/TaskContext';
import { formatDistanceToNow } from 'date-fns';
import { it } from 'date-fns/locale';

export interface Version {
  id: string;
  createdAt: Date;
  label: string;
  description?: string;
  isCurrent: boolean;
  stage: string;
}

interface VersionControlProps {
  onVersionSelect?: (versionId: string) => void;
  onCompareSelect?: (versionIds: [string, string]) => void;
  onDownload?: (versionId: string) => void;
}

const VersionControl: React.FC<VersionControlProps> = ({
  onVersionSelect,
  onCompareSelect,
  onDownload
}) => {
  const theme = useTheme();
  const { task } = useTask();
  const [expanded, setExpanded] = useState(true);
  const [selectedVersions, setSelectedVersions] = useState<string[]>([]);
  
  // Get versions from task context or use mock data for development
  const versions: Version[] = task.versions || [];
  
  const handleCompareClick = () => {
    if (selectedVersions.length === 2 && onCompareSelect) {
      onCompareSelect(selectedVersions as [string, string]);
    }
  };
  
  const handleVersionSelect = (versionId: string) => {
    if (selectedVersions.includes(versionId)) {
      setSelectedVersions(selectedVersions.filter(id => id !== versionId));
    } else {
      if (selectedVersions.length < 2) {
        setSelectedVersions([...selectedVersions, versionId]);
      } else {
        // If already have 2 selected, replace the oldest selection
        setSelectedVersions([...selectedVersions.slice(1), versionId]);
      }
    }
  };
  
  const getStageColor = (stage: string) => {
    const stageColors: Record<string, string> = {
      writer: theme.palette.info.main,
      reviewer: theme.palette.secondary.main,
      refinement: theme.palette.warning.main,
      finalization: theme.palette.success.main,
      default: theme.palette.primary.main
    };
    
    return stageColors[stage] || stageColors.default;
  };
  
  if (!versions || versions.length === 0) {
    return (
      <Paper 
        elevation={1} 
        sx={{ 
          p: 2, 
          mb: 2, 
          borderLeft: `4px solid ${theme.palette.primary.main}`,
          opacity: 0.8
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <HistoryIcon color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6">Cronologia Versioni</Typography>
        </Box>
        <Typography variant="body2" sx={{ mt: 1, fontStyle: 'italic' }}>
          La cronologia delle versioni sarà disponibile dopo il primo salvataggio del documento.
        </Typography>
      </Paper>
    );
  }
  
  return (
    <Paper 
      elevation={1} 
      sx={{ 
        mb: 2, 
        borderLeft: `4px solid ${theme.palette.primary.main}`
      }}
    >
      <Box 
        sx={{ 
          p: 2,
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          borderBottom: expanded ? `1px solid ${theme.palette.divider}` : 'none'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <HistoryIcon color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6">Cronologia Versioni</Typography>
          <Chip 
            label={versions.length} 
            size="small" 
            color="primary" 
            sx={{ ml: 1, height: 20, '& .MuiChip-label': { px: 1 } }} 
          />
        </Box>
        <IconButton onClick={() => setExpanded(!expanded)} size="small">
          {expanded ? <ExpandIcon /> : <CollapseIcon />}
        </IconButton>
      </Box>
      
      <Collapse in={expanded}>
        <List dense disablePadding>
          {versions.map((version, index) => (
            <React.Fragment key={version.id}>
              {index > 0 && <Divider component="li" />}
              <ListItem 
                disablePadding
                sx={{ 
                  px: 2, 
                  py: 1,
                  backgroundColor: selectedVersions.includes(version.id) 
                    ? `${theme.palette.primary.light}20` 
                    : 'transparent',
                  '&:hover': {
                    backgroundColor: `${theme.palette.primary.light}10`
                  }
                }}
                button
                onClick={() => {
                  if (onVersionSelect && !selectedVersions.includes(version.id)) {
                    onVersionSelect(version.id);
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  {version.isCurrent ? (
                    <CurrentIcon color="success" fontSize="small" />
                  ) : (
                    <HistoryIcon fontSize="small" color="action" />
                  )}
                </ListItemIcon>
                
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Typography 
                        variant="body2" 
                        component="span" 
                        sx={{ 
                          fontWeight: version.isCurrent ? 500 : 400,
                          mr: 0.5
                        }}
                      >
                        {version.label}
                      </Typography>
                      
                      <Chip
                        label={version.stage}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: '0.7rem',
                          backgroundColor: getStageColor(version.stage),
                          color: 'white',
                          '& .MuiChip-label': { px: 0.8 }
                        }}
                      />
                    </Box>
                  }
                  secondary={
                    <Typography variant="caption" component="span" color="text.secondary">
                      {formatDistanceToNow(new Date(version.createdAt), { 
                        addSuffix: true, 
                        locale: it 
                      })}
                    </Typography>
                  }
                />
                
                <ListItemSecondaryAction>
                  <Box sx={{ display: 'flex' }}>
                    <Tooltip title="Seleziona per confrontare">
                      <IconButton 
                        edge="end" 
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleVersionSelect(version.id);
                        }}
                        color={selectedVersions.includes(version.id) ? "primary" : "default"}
                      >
                        <CompareIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    
                    <Tooltip title="Visualizza">
                      <IconButton 
                        edge="end" 
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onVersionSelect) onVersionSelect(version.id);
                        }}
                      >
                        <ViewIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    
                    {!version.isCurrent && (
                      <Tooltip title="Ripristina questa versione">
                        <IconButton 
                          edge="end" 
                          size="small"
                          color="warning"
                          onClick={(e) => {
                            e.stopPropagation();
                            // Handle restore version - implementation would depend on your APIs
                            // This would typically call a function from the task context
                          }}
                        >
                          <RestoreIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    
                    <Tooltip title="Scarica">
                      <IconButton 
                        edge="end" 
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onDownload) onDownload(version.id);
                        }}
                      >
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </ListItemSecondaryAction>
              </ListItem>
            </React.Fragment>
          ))}
        </List>
        
        {selectedVersions.length > 0 && (
          <Box sx={{ p: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
            <Typography variant="body2" gutterBottom>
              {selectedVersions.length === 1 
                ? '1 versione selezionata' 
                : `${selectedVersions.length} versioni selezionate`}
            </Typography>
            
            {selectedVersions.length === 2 && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<CompareIcon />}
                onClick={handleCompareClick}
                sx={{ mt: 0.5 }}
              >
                Confronta versioni
              </Button>
            )}
          </Box>
        )}
      </Collapse>
    </Paper>
  );
};

export default VersionControl; 