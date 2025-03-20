# Vercel Deployment Guide

This guide provides instructions for deploying the Insurance Report Generator frontend on Vercel.

## Deploying the Frontend on Vercel

This guide will walk you through deploying the frontend of the Insurance Report Generator application on Vercel.

### Prerequisites

- A Vercel account
- Git repository access
- Access to the backend API endpoint (deployed on Render or elsewhere)

### Setup Steps

1. **Login to Vercel Dashboard**
   - Go to [Vercel](https://vercel.com) and login to your account
   - Click on "Add New..." → "Project"

2. **Import Git Repository**
   - Select your Git provider and repository
   - Find the Insurance Report Generator repository and click "Import"

3. **Configure Project**
   - **Project Name**: Enter a name for your deployment (e.g., insurance-report-generator)
   - **Framework Preset**: Select Next.js
   - **Root Directory**: Set to `/frontend` (important!)
   - **Build and Output Settings**:
     - Build Command: `sh ../scripts/vercel-deploy-setup.sh && npm run build`
     - Output Directory: `.next`
     - Install Command: `npm install`
     - Development Command: `npm run dev`

4. **Environment Variables**
   Set up the following environment variables:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com
   NEXT_PUBLIC_UPLOAD_CHUNK_SIZE=1048576
   NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
   ```
   
   Note: All frontend environment variables MUST be prefixed with `NEXT_PUBLIC_` to be accessible.

5. **Fixing TypeScript Dependencies**
   The deployment setup script (`vercel-deploy-setup.sh`) will handle:
   - Installing TypeScript dependencies
   - Setting up type declarations for external libraries
   - Configuring Next.js to handle TypeScript errors gracefully

   If you encounter issues with the script, you can manually:
   - Ensure your `package.json` includes:
     ```json
     "devDependencies": {
       "typescript": "^4.9.5",
       "@types/node": "^18.15.11",
       "@types/react": "^18.0.33",
       "@types/react-dom": "^18.0.11",
     }
     ```
   - Create a proper `tsconfig.json` file 
   - Add TypeScript declarations for external modules

6. **Handling TypeScript Errors**
   - If you encounter TypeScript errors during build, the setup script adds `ignoreBuildErrors: true` to the TypeScript configuration in `next.config.js`
   - This allows the build to succeed even with TypeScript errors

7. **Deploy**
   - Click "Deploy"
   - Vercel will build and deploy your application

8. **Verify Deployment**
   - Once deployment is complete, click the generated URL to visit your site
   - Verify that the application is working correctly and can communicate with the backend

### Troubleshooting

#### Missing TypeScript Dependencies
If you encounter errors related to TypeScript or missing types:
1. Check that the build command includes the setup script: `sh ../scripts/vercel-deploy-setup.sh && npm run build`
2. Verify the script has execute permissions (`chmod +x ../scripts/vercel-deploy-setup.sh`)
3. Check Vercel logs to see if the script executed properly

#### API Connection Issues
If the frontend cannot connect to the backend:
1. Check the `NEXT_PUBLIC_API_URL` environment variable
2. Make sure CORS is properly configured on the backend
3. Verify that the backend is up and running

#### Module Resolution Errors
If you see errors related to modules not being found:
1. Make sure all dependencies are correctly listed in `package.json`
2. Verify that the build command is installing dependencies properly
3. Check if custom type declarations are needed for third-party modules

### Custom Domain Setup (Optional)

1. Go to your project settings in Vercel
2. Navigate to "Domains"
3. Add your custom domain
4. Follow the instructions to configure DNS settings

### Continuous Deployment

By default, Vercel will deploy your application automatically when changes are pushed to the main branch. You can configure this behavior in the project settings.

## Setting Up the Frontend Project

1. Create a new project on Vercel
2. Connect to your GitHub repository
3. Configure the project with the following settings:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: (Leave as default) `npm run build` or `next build`
   - **Output Directory**: (Leave as default) `.next`

## Fixing Missing Dependencies

Before deploying, ensure all required dependencies are properly installed. Based on deployment logs, you need to add the following dependency:

```bash
# Navigate to your frontend directory
cd frontend

# Install the missing markdown editor dependency
npm install react-simplemde-editor --save

# Commit and push changes
git add package.json package-lock.json
git commit -m "Add missing react-simplemde-editor dependency"
git push
```

## Environment Variables

Add the following environment variables in the Vercel dashboard. Replace placeholder values with your actual production values:

```
# API URL - must point to your Render backend service
NEXT_PUBLIC_API_URL=https://your-backend-service.onrender.com

# Frontend URL (if needed for callbacks)
FRONTEND_URL=https://your-frontend-domain.vercel.app

# Set production mode
NODE_ENV=production
```

## Handling Missing Type Declarations

If you encounter TypeScript errors about missing type declarations, you have two options:

1. **Install types package** (preferred):
   ```bash
   npm install --save-dev @types/react-simplemde-editor
   ```

2. **Create a declaration file** if types aren't available:
   ```typescript
   // Create a file: frontend/types/react-simplemde-editor.d.ts
   declare module 'react-simplemde-editor' {
     import React from 'react';
     export interface SimpleMDEReactProps {
       value: string;
       onChange: (value: string) => void;
       options?: any;
       // Add other props as needed
     }
     const SimpleMDE: React.FC<SimpleMDEReactProps>;
     export default SimpleMDE;
   }
   ```

## Build Optimization

To optimize the build process:

1. Update `next.config.js` to exclude server-side only code from the client bundle:
   ```javascript
   module.exports = {
     // Existing config...
     webpack: (config, { isServer }) => {
       // Only include specific polyfills or packages on the server
       if (!isServer) {
         // Don't bundle server-only dependencies on the client
       }
       return config;
     }
   }
   ```

2. Consider using a `.npmrc` file to avoid legacy dependency warnings:
   ```
   # Create a file: frontend/.npmrc
   legacy-peer-deps=true
   ```

## Post-Deployment Verification

After deployment, verify:

1. The frontend loads correctly without console errors
2. API calls to the backend work properly (check Network tab in browser dev tools)
3. File uploads and processing function correctly
4. The UI is responsive and looks as expected
5. The markdown editor loads and works correctly

## Redeploy After Changes

Whenever you make changes to your codebase and push to your repository:

1. Vercel will automatically redeploy your application
2. You can also manually trigger redeploys from the dashboard
3. For environment variable changes, you may need to redeploy manually

## Note on Environment Variables

If you need to update environment variables:

1. Go to the Vercel dashboard
2. Navigate to your project
3. Click on "Settings" > "Environment Variables"
4. Make your changes
5. Redeploy your application for the changes to take effect 