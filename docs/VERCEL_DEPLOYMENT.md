# Vercel Deployment Guide

This guide provides instructions for deploying the Insurance Report Generator frontend on Vercel.

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

## Deployment Steps

1. Push your code with all necessary dependencies to your GitHub repository
2. In the Vercel dashboard, click "New Project"
3. Import your GitHub repository
4. Configure the project settings as detailed above
5. Add all the required environment variables
6. Click "Deploy"
7. Monitor the build logs for any errors
8. Your frontend will be available at the Vercel-assigned domain (e.g., `https://your-project.vercel.app`)

## Custom Domain (Optional)

1. In the Vercel dashboard, go to your project
2. Click on "Settings" > "Domains"
3. Add your custom domain and follow the DNS configuration instructions

## Post-Deployment Verification

After deployment, verify:

1. The frontend loads correctly without console errors
2. API calls to the backend work properly (check Network tab in browser dev tools)
3. File uploads and processing function correctly
4. The UI is responsive and looks as expected
5. The markdown editor loads and works correctly

## Troubleshooting

If you encounter issues during deployment, please refer to the [Frontend Deployment Fixes](./FRONTEND_DEPLOYMENT_FIXES.md) document for detailed solutions to common problems.

### Common Issues

1. **Missing Module Errors**: If you see errors about missing modules like `react-simplemde-editor`, refer to the [Frontend Deployment Fixes](./FRONTEND_DEPLOYMENT_FIXES.md#missing-module-issues) section.

2. **TypeScript Errors**: If you encounter TypeScript-related errors, see our detailed solutions in the [Frontend TypeScript Fix](./FRONTEND_TYPESCRIPT_FIX.md) document.

3. **Build Performance**: For slow builds or timeouts, see our optimization recommendations in the [Frontend Deployment Fixes](./FRONTEND_DEPLOYMENT_FIXES.md#build-performance-issues) section.

4. **API Connection Issues**: If your frontend can't connect to the backend, check the environment variable configuration as detailed in [Frontend Deployment Fixes](./FRONTEND_DEPLOYMENT_FIXES.md#environment-variable-configuration).

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