import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box, Container } from '@mui/material';
import Link from 'next/link';
import { useRouter } from 'next/router';

const Navbar: React.FC = () => {
  const router = useRouter();
  
  // Function to determine if a route is active
  const isActive = (path: string) => router.pathname === path;
  
  return (
    <AppBar position="sticky" elevation={0}>
      <Container maxWidth="lg">
        <Toolbar sx={{ py: 1 }}>
          <Typography 
            variant="h4" 
            component="div" 
            sx={{ 
              flexGrow: 1, 
              fontWeight: 600,
              fontSize: { xs: '1.1rem', sm: '1.3rem' }
            }}
          >
            Generatore di Perizie
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Link href="/" passHref>
              <Button 
                color="primary"
                variant={isActive('/') ? "contained" : "text"}
                sx={{ 
                  color: isActive('/') ? '#fff' : 'text.primary',
                  fontWeight: 500
                }}
              >
                Home
              </Button>
            </Link>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Navbar; 