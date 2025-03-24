import React from 'react';
import type { NextPage } from 'next';
import Head from 'next/head';
import TaskDashboard from '../components/TaskDashboard';

const Home: NextPage = () => {
  return (
    <>
      <Head>
        <title>Insurance Report Generator</title>
        <meta name="description" content="Generate professional insurance reports with AI assistance" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <main>
        {/* Using TaskDashboard as the main application interface */}
        <TaskDashboard />
      </main>
    </>
  );
};

export default Home; 