# Production Deployment Checklist

This checklist helps ensure that your Insurance Report Generator application is properly configured for production deployment. Go through each item before deploying to Vercel (frontend) and Render (backend).

## Backend (Render) Preparation

- [ ] Fix any import errors in the codebase (check for missing imports like `UploadQueryResult`)
- [ ] Ensure all Python packages are in `requirements.txt` at the root (not just in backend folder)
- [ ] Update the start command to use `python -m uvicorn` for proper module resolution
- [ ] Set correct file paths for `UPLOAD_DIR` and `GENERATED_REPORTS_DIR` using `/opt/render/project/src/` prefix
- [ ] Ensure `__init__.py` files exist in all directories to make them proper packages
- [ ] Verify that storage directories will be properly created on startup

## Frontend (Vercel) Preparation

- [ ] Install all required dependencies, especially `react-simplemde-editor`
- [ ] Fix any TypeScript type definition errors (add `@types` packages or create declaration files)
- [ ] Ensure proper dynamic imports with `{ ssr: false }` for browser-only components
- [ ] Add `.npmrc` file with `legacy-peer-deps=true` if needed
- [ ] Fix any Next.js build warnings that could become errors in production

## Environment Variables

### Backend (Render)

- [ ] Create all required environment variables on Render (see `docs/RENDER_DEPLOYMENT.md`)
- [ ] Set `NODE_ENV=production`
- [ ] Set `DEBUG=false`
- [ ] Configure `FRONTEND_URL` with comma-separated list of production frontend URLs
- [ ] Set `CORS_ALLOW_ALL=false`
- [ ] Set appropriate `API_RATE_LIMIT` for production traffic
- [ ] Configure `DEFAULT_MODEL` to the preferred production model
- [ ] Configure `UPLOAD_DIR` and `GENERATED_REPORTS_DIR` to use correct paths for Render
- [ ] Ensure API keys are valid and have sufficient quotas

### Frontend (Vercel)

- [ ] Set `NEXT_PUBLIC_API_URL` to the production backend URL on Render
- [ ] Set `NODE_ENV=production`

## Security

- [ ] Ensure sensitive files are in `.gitignore` (e.g., `.env`)
- [ ] Verify CORS settings only allow production domains
- [ ] Check file permissions for upload directories
- [ ] Check API rate limiting configurations
- [ ] Consider enabling authentication for production

## Data Storage

- [ ] Configure persistent storage on Render (if using local file storage)
- [ ] Ensure regular backups of Supabase data
- [ ] Verify file cleanup processes are working

## Testing

- [ ] Run tests on production configuration
- [ ] Verify API endpoints work with production settings
- [ ] Test file uploads and downloads
- [ ] Test report generation
- [ ] Verify CORS is properly configured

## Monitoring

- [ ] Set up monitoring for the `/health` endpoint
- [ ] Configure logging for production (less verbose)
- [ ] Set up alerts for service disruptions

## Domain Configuration

- [ ] Configure custom domains in Vercel (if applicable)
- [ ] Set up SSL certificates for custom domains
- [ ] Update CORS settings if using custom domains

## Post-Deployment Verification

- [ ] Verify frontend loads correctly without JavaScript errors
- [ ] Test API connectivity from the frontend (check browser Network tab)
- [ ] Verify all components load, especially the Markdown editor
- [ ] Verify file uploads work
- [ ] Verify report generation works
- [ ] Check that static assets are loading properly

## Error Monitoring

- [ ] Check Render logs for any startup errors (especially import or module errors)
- [ ] Check Vercel build logs for any build failures
- [ ] Setup error tracking for runtime errors
- [ ] Have a plan for quickly fixing deployment issues

## Rollback Plan

- [ ] Document steps to roll back to previous version if needed
- [ ] Ensure database backups are available
- [ ] Know how to quickly revert to previous deployment on Vercel/Render

## Performance Optimization

- [ ] Enable caching where appropriate
- [ ] Verify frontend builds are optimized
- [ ] Check for resource-intensive operations that might need optimization

## Documentation

- [ ] Update API documentation with production URLs
- [ ] Document deployment process for team members
- [ ] Update README with production information

## Legal and Compliance

- [ ] Ensure privacy policy is up to date
- [ ] Verify compliance with data protection regulations
- [ ] Check licensing requirements for production use 