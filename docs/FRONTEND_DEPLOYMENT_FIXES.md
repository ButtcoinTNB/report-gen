# Frontend Deployment Fixes

This document outlines the issues encountered during deployment of the frontend application to Vercel, along with their solutions.

## Missing Module Issues

### Problem: Missing Module `react-simplemde-editor`

The deployment was failing with the following error:
```
Cannot find module 'react-simplemde-editor'
```

This error occurred because:
1. The dependency was listed in the code imports but was either missing from `package.json` or was not being properly installed during the build process.
2. TypeScript declarations might be missing for this module.

### Solution:

1. **Add the missing dependency**: Update `package.json` to include the dependency:
   ```bash
   cd frontend
   npm install --save react-simplemde-editor
   npm install --save-dev @types/react-simplemde-editor
   ```

2. **Create TypeScript declaration file**: If type definitions are still missing, create a declaration file in your project:
   ```typescript
   // frontend/types/react-simplemde-editor.d.ts
   declare module 'react-simplemde-editor' {
     import * as React from 'react';
     
     interface SimpleMDEEditorProps {
       value: string;
       onChange: (value: string) => void;
       options?: any;
       events?: any;
       className?: string;
       id?: string;
     }
     
     const SimpleMDEEditor: React.ComponentType<SimpleMDEEditorProps>;
     export default SimpleMDEEditor;
   }
   ```

3. **Update `tsconfig.json`**: Ensure your TypeScript configuration includes the custom type declarations:
   ```json
   {
     "compilerOptions": {
       "typeRoots": ["./node_modules/@types", "./types"]
     }
   }
   ```

## Build Performance Issues

### Problem: Slow Builds or Timeouts

Large frontends can sometimes time out during the build process on hosting platforms.

### Solution:

1. **Optimize build settings**: Add a `.vercelignore` file to exclude unnecessary files:
   ```
   .git
   node_modules
   docs
   ```

2. **Implement build caching**: Add caching to your Next.js build by configuring `next.config.js`:
   ```javascript
   module.exports = {
     experimental: {
       turbotrace: {
         logLevel: 'error'
       }
     },
     swcMinify: true,
   };
   ```

## Environment Variable Configuration

### Problem: Missing Environment Variables

The frontend was unable to connect to the backend API due to missing or incorrectly configured environment variables.

### Solution:

1. **Add required environment variables to Vercel**:
   - Go to your Vercel project settings
   - Add the following environment variables:
     ```
     NEXT_PUBLIC_API_URL=https://your-render-app.onrender.com
     NEXT_PUBLIC_APP_ENV=production
     ```

2. **Create environment fallbacks**: Update your environment configuration to include fallbacks for missing variables:
   ```javascript
   // frontend/utils/config.js
   export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
   export const APP_ENV = process.env.NEXT_PUBLIC_APP_ENV || 'development';
   ```

## General Deployment Tips

1. **Check dependencies before deployment**:
   ```bash
   npm ls react-simplemde-editor
   ```

2. **Run a local production build**:
   ```bash
   npm run build
   ```

3. **Analyze bundle size**:
   ```bash
   npm install -g next-bundle-analyzer
   # Then add the analyzer to next.config.js
   ```

4. **Test API endpoints against CORS**:
   Ensure your backend CORS settings allow requests from your Vercel domain.

Remember to review the [Vercel Deployment Guide](./VERCEL_DEPLOYMENT.md) for complete setup instructions. 