import React, { useEffect, useState } from 'react';
import { Box, Chip, CircularProgress, Alert, Typography, Tooltip } from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import { useAppSelector, useAppDispatch } from '../store/hooks';
import { RootState } from '../store/index';
import { AgentLoopState, detectStalledAgentLoop } from '../store/reportSlice';
import { isBrowser, runInBrowser, browserOnly } from '../utils/environment';

interface AgentInitializationTrackerProps {
  onStalled?: () => void;
}

const AgentInitializationTracker: React.FC<AgentInitializationTrackerProps> = ({ onStalled }) => {
  const agentLoop = useAppSelector((state: RootState) => state.report.agentLoop);
  const dispatch = useAppDispatch();
  const [elapsedTime, setElapsedTime] = useState<number>(0);

  // Format time in mm:ss format
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Format estimated time remaining
  const formatEstimatedTime = (agentLoop: AgentLoopState): string => {
    if (agentLoop.estimatedTimeRemaining === null || agentLoop.estimatedTimeRemaining === undefined) {
      return "Calculating...";
    }
    
    if (agentLoop.estimatedTimeRemaining <= 0) {
      return "Almost complete";
    }
    
    const mins = Math.floor(agentLoop.estimatedTimeRemaining / 60);
    const secs = Math.floor(agentLoop.estimatedTimeRemaining % 60);
    
    if (mins > 0) {
      return `~${mins}m ${secs}s remaining`;
    }
    return `~${secs}s remaining`;
  };

  // Check if the agent loop is active (either initializing or running)
  const isAgentActive = agentLoop.isInitializing || agentLoop.isRunning;

  // Manage elapsed time and check for stalled state
  useEffect(() => {
    let interval: number | undefined;
    
    // Only track time when the agent loop is active and we're in a browser
    if (isAgentActive) {
      // Start counting elapsed time - only in browser
      runInBrowser(() => {
        interval = window.setInterval(() => {
          setElapsedTime((prev) => prev + 1);
          
          // Check for stalled state every 10 seconds
          if (elapsedTime % 10 === 0) {
            dispatch(detectStalledAgentLoop({}));
          }
        }, 1000);
      });
      
      // Call the onStalled callback if the process stalled and the callback is provided
      if (agentLoop.isStalled && onStalled) {
        onStalled();
      }
    } else {
      // Reset elapsed time when the agent loop stops
      setElapsedTime(0);
    }
    
    // Cleanup function
    return () => {
      runInBrowser(() => {
        if (interval !== undefined) {
          clearInterval(interval);
        }
      });
    };
  }, [isAgentActive, agentLoop.isStalled, elapsedTime, dispatch, onStalled]);
  
  if (!isAgentActive) {
    return null;
  }

  return (
    <Box sx={{ mt: 2, mb: 3 }}>
      {agentLoop.isStalled && (
        <Alert 
          severity="warning" 
          sx={{ 
            mb: 2, 
            animation: 'pulse 2s infinite',
            '@keyframes pulse': {
              '0%': { opacity: 0.8 },
              '50%': { opacity: 1 },
              '100%': { opacity: 0.8 }
            }
          }}
        >
          The process seems to be taking longer than expected. Please wait...
        </Alert>
      )}
      
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: 2,
        p: 2,
        border: '1px solid #e0e0e0',
        borderRadius: 1,
        bgcolor: 'background.paper',
        boxShadow: 1
      }}>
        <Box 
          sx={{ 
            animation: 'spin 2s linear infinite',
            '@keyframes spin': {
              '0%': { transform: 'rotate(0deg)' },
              '100%': { transform: 'rotate(360deg)' }
            }
          }}
        >
          <CircularProgress 
            size={40} 
            variant="determinate" 
            value={agentLoop.progress || 0} 
            color={agentLoop.isStalled ? "warning" : "primary"}
          />
        </Box>
        
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="body1" fontWeight="medium">
            {agentLoop.message || "Processing..."}
          </Typography>
          
          <Typography 
            variant="body2" 
            color="text.secondary"
            sx={{ mt: 0.5 }}
          >
            {agentLoop.stage ? (
              `Stage: ${agentLoop.stage.charAt(0).toUpperCase() + agentLoop.stage.slice(1)}`
            ) : (
              "Initializing..."
            )}
          </Typography>
        </Box>
        
        <Tooltip title="Elapsed time">
          <Chip 
            icon={<AccessTimeIcon />} 
            label={formatTime(elapsedTime)}
            size="small"
            color="default"
            variant="outlined"
          />
        </Tooltip>
        
        {agentLoop.estimatedTimeRemaining !== null && (
          <Tooltip title="Estimated time remaining">
            <Chip 
              icon={<HourglassEmptyIcon />} 
              label={formatEstimatedTime(agentLoop)}
              size="small"
              color="primary"
              variant="outlined"
            />
          </Tooltip>
        )}
      </Box>
    </Box>
  );
};

export default AgentInitializationTracker; 