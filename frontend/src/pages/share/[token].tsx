import React from 'react';
import { useRouter } from 'next/router';
import { Container, Box } from '@mui/material';
import { ShareLinkViewer } from '../../components/ShareLinkViewer';

const SharePage: React.FC = () => {
  const router = useRouter();
  const { token } = router.query;

  if (!token || typeof token !== 'string') {
    return null;
  }

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <ShareLinkViewer token={token} />
      </Box>
    </Container>
  );
};

export default SharePage; 