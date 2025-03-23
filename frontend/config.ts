/**
 * Frontend configuration
 * Manages environment variables for API URLs and other settings
 */

// In production (Vercel), use the NEXT_PUBLIC_API_URL environment variable
// In development, fall back to localhost
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Define endpoint structure
interface Endpoints {
  upload: string;
  generate: string;
  format: string;
  edit: string;
  download: string;
}

// Define config structure
interface Config {
  API_URL: string;
  endpoints: Endpoints;
}

// Warning structure for environment variable validation
interface EnvWarning {
  variable: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

// Result of environment variable validation
export interface EnvValidationResult {
  isValid: boolean;
  warnings: EnvWarning[];
}

// Define config object with safe defaults
export const config: Config = {
  API_URL,
  endpoints: {
    upload: `${API_URL}/api/upload`,
    generate: `${API_URL}/api/generate`,
    format: `${API_URL}/api/format`,
    edit: `${API_URL}/api/edit`,
    download: `${API_URL}/api/download`,
  }
};

// For TypeScript safety, ensure all config properties are defined
Object.keys(config).forEach(key => {
  if (config[key as keyof Config] === undefined) {
    console.warn(`Missing configuration for ${key}, using fallback value`);
    
    // Set fallback values for different config types
    if (key === 'API_URL') {
      (config as any)[key] = 'http://localhost:8000';
    }
  }
});

/**
 * Validates required environment variables and logs warnings if any are missing
 * @returns {EnvValidationResult} Object containing validation results
 */
export function validateEnvVars(): EnvValidationResult {
  const warnings: EnvWarning[] = [];
  
  // Check API URL
  if (!process.env.NEXT_PUBLIC_API_URL) {
    warnings.push({
      variable: 'NEXT_PUBLIC_API_URL',
      message: 'API URL not set, using localhost. This may not work in production.',
      severity: 'warning'
    });
  }
  
  // Log warnings during development
  if (process.env.NODE_ENV !== 'production' && warnings.length > 0) {
    console.warn('⚠️ Environment variable warnings:');
    warnings.forEach(warning => {
      console.warn(`- ${warning.variable}: ${warning.message}`);
    });
  }
  
  return {
    isValid: warnings.length === 0,
    warnings
  };
}

// Validate on import (only in browser environment)
if (typeof window !== 'undefined') {
  validateEnvVars();
}

export default config; 