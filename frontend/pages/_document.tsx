import { Html, Head, Main, NextScript } from 'next/document';
import { DocumentProps } from 'next/document';
import React from 'react';

export default function Document(): React.JSX.Element {
  return (
    <Html lang="en">
      <Head>
        <meta charSet="utf-8" />
        <meta name="description" content="Scrittore Automatico di Perizie - Create formatted reports from case documents" />
        
        {/* Favicon links for better cross-platform support */}
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
        <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
        <link rel="icon" href="/favicon.ico" />
        <link rel="manifest" href="/site.webmanifest" />
        
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css?family=Roboto:300,400,500,700&display=swap"
        />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
} 