import React, { useState } from 'react';
import {
  Button,
  IconButton,
  Tooltip,
  Box,
  Typography,
  CircularProgress,
  Snackbar,
  Alert,
} from '@mui/material';
import { Share as ShareIcon, ContentCopy as CopyIcon } from '@mui/icons-material';
import { ShareService } from '../services/ShareService';

interface ShareButtonProps {
  documentId: string;
  disabled?: boolean;
}

export const ShareButton: React.FC<ShareButtonProps> = ({ documentId, disabled = false }) => {
  const [isSharing, setIsSharing] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [showCopySuccess, setShowCopySuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleShare = async () => {
    setIsSharing(true);
    setError(null);

    try {
      const shareService = ShareService.getInstance();
      const result = await shareService.createShareLink(documentId);
      setShareUrl(result.url);
    } catch (err) {
      setError('Failed to create share link. Please try again.');
      console.error('Share error:', err);
    } finally {
      setIsSharing(false);
    }
  };

  const handleCopy = async () => {
    if (!shareUrl) return;

    try {
      await navigator.clipboard.writeText(shareUrl);
      setShowCopySuccess(true);
    } catch (err) {
      setError('Failed to copy link. Please try again.');
      console.error('Copy error:', err);
    }
  };

  const handleCloseSnackbar = () => {
    setShowCopySuccess(false);
    setError(null);
  };

  return (
    <>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Button
          variant="outlined"
          startIcon={isSharing ? <CircularProgress size={20} /> : <ShareIcon />}
          onClick={handleShare}
          disabled={disabled || isSharing}
        >
          {isSharing ? 'Generating Link...' : 'Share Report'}
        </Button>

        {shareUrl && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              p: 2,
              bgcolor: 'grey.100',
              borderRadius: 1,
            }}
          >
            <Typography
              variant="body2"
              sx={{
                flexGrow: 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {shareUrl}
            </Typography>
            <Tooltip title="Copy Link">
              <IconButton onClick={handleCopy} size="small">
                <CopyIcon />
              </IconButton>
            </Tooltip>
          </Box>
        )}
      </Box>

      <Snackbar
        open={showCopySuccess}
        autoHideDuration={3000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity="success">
          Link copied to clipboard!
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!error}
        autoHideDuration={5000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity="error">
          {error}
        </Alert>
      </Snackbar>
    </>
  );
}; 