import React from 'react';
import { Container, Box, Typography, Paper } from '@mui/material';
import Navbar from '../components/Navbar';
import { ReportStepper } from '../src/components';
import type { NextPage } from 'next';

const Home: NextPage = () => {
  return (
    <>
      <Navbar />
      <Container maxWidth="lg" sx={{ pt: 4, pb: 8 }}>
        <Box sx={{ mb: 4, textAlign: 'center' }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Generatore di Perizie
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Genera perizie assicurative utilizzando l'intelligenza artificiale
          </Typography>
        </Box>
        
        <Paper elevation={3} sx={{ p: 4, borderRadius: 2 }}>
          <ReportStepper />
        </Paper>
        
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            © {new Date().getFullYear()} Insurance Report Generator
          </Typography>
        </Box>
      </Container>
    </>
  );
};

export default Home; 