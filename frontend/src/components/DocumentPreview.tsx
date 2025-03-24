import React, { useRef, useState, useCallback, useEffect } from 'react';
import { Box, IconButton, Typography, CircularProgress, Alert, Button } from '@mui/material';
import {
  Fullscreen as FullscreenIcon,
  FullscreenExit as FullscreenExitIcon,
  NavigateBefore as NavigateBeforeIcon,
  NavigateNext as NavigateNextIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { ZoomIn, ZoomOut } from '@mui/icons-material';
import { PREVIEW, UI, ERROR_MESSAGES } from '../constants/app';
import { debounce } from '../utils/common';

interface DocumentPreviewProps {
  previewUrl: string;
  title: string;
  isLoading: boolean;
  error: string;
  onRefresh: () => Promise<void>;
  className?: string;
}

export const DocumentPreview: React.FC<DocumentPreviewProps> = ({
  previewUrl,
  title,
  isLoading,
  error,
  onRefresh,
  className
}) => {
  const [zoom, setZoom] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  const previewRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleZoomIn = useCallback(debounce(() => {
    setZoom(prev => Math.min(prev + PREVIEW.ZOOM_STEP, PREVIEW.MAX_ZOOM));
  }, UI.DEBOUNCE_DELAY), []);

  const handleZoomOut = useCallback(debounce(() => {
    setZoom(prev => Math.max(prev - PREVIEW.ZOOM_STEP, PREVIEW.MIN_ZOOM));
  }, UI.DEBOUNCE_DELAY), []);

  const handlePageChange = useCallback((delta: number) => {
    setCurrentPage(prev => {
      const newPage = prev + delta;
      return Math.max(1, Math.min(newPage, totalPages));
    });
  }, [totalPages]);

  const handleFullscreen = useCallback(async () => {
    if (!previewRef.current) return;

    try {
      if (!isFullscreen) {
        await previewRef.current.requestFullscreen();
        setIsFullscreen(true);
      } else {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch (err) {
      console.error('Fullscreen error:', err);
    }
  }, [isFullscreen]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  useEffect(() => {
    const fetchDocumentMetadata = async () => {
      try {
        const response = await fetch(`/api/documents/metadata?url=${encodeURIComponent(previewUrl)}`);
        if (!response.ok) throw new Error('Failed to load document metadata');
        
        const data = await response.json();
        setTotalPages(data.pageCount || 1);
      } catch (err) {
        console.error('Error fetching document metadata:', err);
      }
    };

    if (previewUrl) {
      fetchDocumentMetadata();
    }
  }, [previewUrl]);

  useEffect(() => {
    const handleKeyboard = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') handlePageChange(-1);
      if (e.key === 'ArrowRight') handlePageChange(1);
      if (e.key === 'Escape' && isFullscreen) handleFullscreen();
    };

    window.addEventListener('keydown', handleKeyboard);
    return () => window.removeEventListener('keydown', handleKeyboard);
  }, [handlePageChange, isFullscreen, handleFullscreen]);

  const handlePreviousPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  };

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(totalPages, prev + 1));
  };

  if (error) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          p: 4,
          gap: 2,
          bgcolor: 'background.paper',
          borderRadius: 1,
        }}
        className={className}
      >
        <Typography color="error" gutterBottom>
          {error}
        </Typography>
        <Button onClick={onRefresh} startIcon={<RefreshIcon />}>
          Retry
        </Button>
      </Box>
    );
  }

  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          p: 4,
          bgcolor: 'background.paper',
          borderRadius: 1,
        }}
        className={className}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box
      ref={containerRef}
      className={className}
      sx={{
        position: 'relative',
        width: '100%',
        height: isFullscreen ? '100vh' : PREVIEW.DEFAULT_HEIGHT,
        overflow: 'hidden',
        bgcolor: 'background.paper',
        borderRadius: 1,
        boxShadow: 1
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 1,
          borderBottom: 1,
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton
            onClick={handlePreviousPage}
            disabled={currentPage <= 1}
            size="small"
          >
            <NavigateBeforeIcon />
          </IconButton>
          <Typography variant="body2">
            Page {currentPage} of {totalPages}
          </Typography>
          <IconButton
            onClick={handleNextPage}
            disabled={currentPage >= totalPages}
            size="small"
          >
            <NavigateNextIcon />
          </IconButton>
        </Box>
        <IconButton onClick={handleFullscreen} size="small">
          {isFullscreen ? <FullscreenExitIcon /> : <FullscreenIcon />}
        </IconButton>
      </Box>

      <Box
        ref={previewRef}
        sx={{
          position: 'relative',
          width: '100%',
          height: isFullscreen ? '100vh' : '70vh',
          bgcolor: 'grey.100',
        }}
      >
        <iframe
          src={`${previewUrl}#page=${currentPage}`}
          title={title}
          width="100%"
          height="100%"
          style={{ border: 'none' }}
        />
      </Box>

      <Box
        sx={{
          position: 'absolute',
          bottom: 16,
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          bgcolor: 'rgba(255, 255, 255, 0.9)',
          borderRadius: 1,
          padding: 1,
          boxShadow: 1
        }}
      >
        <IconButton
          onClick={() => handleZoomOut()}
          disabled={zoom <= PREVIEW.MIN_ZOOM}
          aria-label="Zoom out"
        >
          <ZoomOut />
        </IconButton>
        
        <Typography variant="body2" sx={{ minWidth: 60, textAlign: 'center' }}>
          {zoom}%
        </Typography>
        
        <IconButton
          onClick={() => handleZoomIn()}
          disabled={zoom >= PREVIEW.MAX_ZOOM}
          aria-label="Zoom in"
        >
          <ZoomIn />
        </IconButton>
      </Box>
    </Box>
  );
};

export default DocumentPreview; 