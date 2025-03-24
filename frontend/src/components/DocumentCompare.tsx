import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Divider,
  Grid,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  useTheme
} from '@mui/material';
import {
  AddCircleOutline as AddedIcon,
  RemoveCircleOutline as RemovedIcon,
  ChangeCircle as ChangedIcon
} from '@mui/icons-material';
import { useTask } from '../context/TaskContext';
import reportService from '../services/ReportService';

interface DocumentCompareProps {
  versionIds: [string, string];
}

type ChangeType = 'addition' | 'deletion' | 'modification';

interface DocumentChange {
  type: ChangeType;
  section: string;
  content: string;
}

const DocumentCompare: React.FC<DocumentCompareProps> = ({ versionIds }) => {
  const theme = useTheme();
  const { task } = useTask();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [diff, setDiff] = useState<string>('');
  const [changes, setChanges] = useState<DocumentChange[]>([]);
  const [versions, setVersions] = useState<[any, any]>([null, null]);

  useEffect(() => {
    const loadComparison = async () => {
      if (!versionIds || versionIds.length !== 2) {
        setError('Two valid version IDs are required for comparison');
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // Get the versions information
        const v1 = task.versions?.find(v => v.id === versionIds[0]) || null;
        const v2 = task.versions?.find(v => v.id === versionIds[1]) || null;
        setVersions([v1, v2]);

        // Get the comparison data
        const result = await reportService.compareVersions(versionIds[0], versionIds[1]);
        setDiff(result.diff);
        setChanges(result.changes);
      } catch (err) {
        console.error('Failed to load comparison:', err);
        setError('Failed to compare documents. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadComparison();
  }, [versionIds, task.versions]);

  // Get color for change type
  const getChangeColor = (type: ChangeType): string => {
    switch (type) {
      case 'addition':
        return theme.palette.success.main;
      case 'deletion':
        return theme.palette.error.main;
      case 'modification':
        return theme.palette.warning.main;
      default:
        return theme.palette.text.primary;
    }
  };

  // Get icon for change type
  const getChangeIcon = (type: ChangeType) => {
    switch (type) {
      case 'addition':
        return <AddedIcon sx={{ color: getChangeColor(type) }} />;
      case 'deletion':
        return <RemovedIcon sx={{ color: getChangeColor(type) }} />;
      case 'modification':
        return <ChangedIcon sx={{ color: getChangeColor(type) }} />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      {/* Version info header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Document Comparison
        </Typography>
        
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Paper 
              elevation={1} 
              sx={{ p: 2, borderLeft: `4px solid ${theme.palette.primary.main}` }}
            >
              <Typography variant="subtitle1" fontWeight="bold">
                Original Version
              </Typography>
              <Typography variant="body2">
                {versions[0]?.label || 'Unknown version'} 
                {' - '}
                {new Date(versions[0]?.createdAt).toLocaleString()}
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={6}>
            <Paper 
              elevation={1} 
              sx={{ p: 2, borderLeft: `4px solid ${theme.palette.secondary.main}` }}
            >
              <Typography variant="subtitle1" fontWeight="bold">
                Updated Version
              </Typography>
              <Typography variant="body2">
                {versions[1]?.label || 'Unknown version'}
                {' - '}
                {new Date(versions[1]?.createdAt).toLocaleString()}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>

      {/* Change summary */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Summary of Changes
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Chip
            icon={<AddedIcon />}
            label={`${changes.filter(c => c.type === 'addition').length} Additions`}
            color="success"
            variant="outlined"
            size="small"
          />
          <Chip
            icon={<RemovedIcon />}
            label={`${changes.filter(c => c.type === 'deletion').length} Deletions`}
            color="error"
            variant="outlined"
            size="small"
          />
          <Chip
            icon={<ChangedIcon />}
            label={`${changes.filter(c => c.type === 'modification').length} Modifications`}
            color="warning"
            variant="outlined"
            size="small"
          />
        </Box>
        
        <List sx={{ bgcolor: 'background.paper' }}>
          {changes.map((change, index) => (
            <React.Fragment key={index}>
              {index > 0 && <Divider component="li" />}
              <ListItem alignItems="flex-start">
                <ListItemIcon>
                  {getChangeIcon(change.type)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography 
                      variant="subtitle2" 
                      sx={{ color: getChangeColor(change.type) }}
                    >
                      {change.section} ({change.type})
                    </Typography>
                  }
                  secondary={
                    <Typography 
                      variant="body2" 
                      component="span" 
                      sx={{ display: 'inline' }}
                    >
                      {change.content}
                    </Typography>
                  }
                />
              </ListItem>
            </React.Fragment>
          ))}
        </List>
      </Box>

      {/* Visual diff */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Detailed Comparison
        </Typography>
        
        <Paper 
          elevation={1} 
          sx={{ 
            p: 3,
            maxHeight: '500px',
            overflow: 'auto',
            whiteSpace: 'pre-wrap',
            fontSize: '0.9rem',
            fontFamily: 'monospace',
            '& ins': {
              backgroundColor: `${theme.palette.success.light}40`,
              textDecoration: 'none',
              padding: '0 2px',
            },
            '& del': {
              backgroundColor: `${theme.palette.error.light}40`,
              textDecoration: 'line-through',
              padding: '0 2px',
            }
          }}
        >
          <div dangerouslySetInnerHTML={{ __html: diff }} />
        </Paper>
      </Box>
    </Box>
  );
};

export default DocumentCompare; 