import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Paper,
  LinearProgress,
} from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';
import { ShareService } from '../services/ShareService';
import { formatDistanceToNow } from 'date-fns';

interface ShareLinkViewerProps {
  token: string;
}

interface ShareLinkInfo {
  url: string;
  expiresAt: Date;
  remainingDownloads: number;
  documentId: string;
}

export const ShareLinkViewer: React.FC<ShareLinkViewerProps> = ({ token }) => {
  const [info, setInfo] = useState<ShareLinkInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);

  useEffect(() => {
    loadShareLinkInfo();
  }, [token]);

  const loadShareLinkInfo = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const shareService = ShareService.getInstance();
      const result = await shareService.getShareLinkInfo(token);
      setInfo({
        ...result,
        expiresAt: new Date(result.expiresAt),
      });
    } catch (err) {
      setError('This share link is invalid or has expired.');
      console.error('Error loading share link info:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!info) return;

    setIsDownloading(true);
    setDownloadProgress(0);
    setError(null);

    try {
      const shareService = ShareService.getInstance();
      await shareService.trackDownload(token);

      // Simulate download progress
      const progressInterval = setInterval(() => {
        setDownloadProgress((prev) => {
          const next = prev + 10;
          if (next >= 100) {
            clearInterval(progressInterval);
          }
          return next;
        });
      }, 500);

      // TODO: Implement actual file download
      // For now, we'll just simulate it
      await new Promise((resolve) => setTimeout(resolve, 5000));

      clearInterval(progressInterval);
      setDownloadProgress(100);

      // Refresh share link info after download
      await loadShareLinkInfo();
    } catch (err) {
      setError('Failed to download the document. Please try again.');
      console.error('Download error:', err);
    } finally {
      setIsDownloading(false);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !info) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error || 'Unable to load share link information.'}
      </Alert>
    );
  }

  return (
    <Paper sx={{ p: 3, m: 2 }}>
      <Typography variant="h5" gutterBottom>
        Shared Document
      </Typography>

      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          This link expires {formatDistanceToNow(info.expiresAt, { addSuffix: true })}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Downloads remaining: {info.remainingDownloads}
        </Typography>
      </Box>

      <Button
        variant="contained"
        startIcon={isDownloading ? <CircularProgress size={20} /> : <DownloadIcon />}
        onClick={handleDownload}
        disabled={isDownloading || info.remainingDownloads === 0}
        fullWidth
      >
        {isDownloading ? 'Downloading...' : 'Download Document'}
      </Button>

      {isDownloading && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress variant="determinate" value={downloadProgress} />
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
            {downloadProgress}%
          </Typography>
        </Box>
      )}

      {info.remainingDownloads === 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          This share link has reached its maximum number of downloads.
        </Alert>
      )}
    </Paper>
  );
}; 