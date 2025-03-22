import { lazy } from 'react';

// Export all components from this directory
export { default as ReportStepper } from './ReportStepper';
export { default as FileUploader } from './FileUploader';

// Lazy loaded components for better performance
export const DocxPreviewEditor = lazy(() => import('./DocxPreviewEditor').then(module => ({ default: module.DocxPreviewEditor })));
export const JourneyVisualizer = lazy(() => import('./JourneyVisualizer'));
export const ReportGenerator = lazy(() => import('./ReportGenerator'));

// Named exports
export const AgentLoopRunner = lazy(() => import('./AgentLoopRunner').then(module => ({ default: module.AgentLoopRunner })));
export const AgentProgressStep = lazy(() => import('./AgentProgressStep').then(module => ({ default: module.AgentProgressStep })));

// Regular exports for smaller components
// export { default as AdditionalInfoInput } from './AdditionalInfoInput';

// Make sure these components are exported if they exist in your project
// export { default as Navbar } from '../../components/Navbar';
// export { default as PDFPreview } from '../../components/PDFPreview';
// export { default as ReportPreview } from '../../components/ReportPreview';
// export { default as DownloadReport } from '../../components/DownloadReport';
// export { default as FileUpload } from '../../components/FileUpload';

export { default as UploadProgressTracker } from './UploadProgressTracker';
export { default as AdditionalInfo } from './AdditionalInfo';
export { default as ReportEditor } from './ReportEditor';
export { default as ReportDownloader } from './ReportDownloader';
export { default as LoadingIndicator } from './LoadingIndicator';
export { default as PDFPreview } from './PDFPreview';
export { default as AgentInitializationTracker } from './AgentInitializationTracker';
export { default as ReportPreview } from './ReportPreview';
export { default as DownloadReport } from './DownloadReport'; 