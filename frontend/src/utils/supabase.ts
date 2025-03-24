import { createClient } from '@supabase/supabase-js';
import { isBrowser, isServer } from './environment';

// Environment variables are accessible in Next.js both client and server side
// https://nextjs.org/docs/basic-features/environment-variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

// Cache duration in seconds
const CACHE_DURATION = {
  SHORT: 60, // 1 minute
  MEDIUM: 300, // 5 minutes
  LONG: 1800, // 30 minutes
};

// Helper to generate random IDs that works in both browser and Node environments
const generateUUID = () => {
  if (isBrowser && window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  } else if (isServer) {
    try {
      // Using require to avoid bundling crypto in client
      const nodeCrypto = require('crypto');
      return nodeCrypto.randomUUID();
    } catch (error) {
      // Fallback for older Node versions or if crypto isn't available
      return `id-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
    }
  } else {
    // Fallback for browsers without crypto support
    return `id-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
  }
};

// Type for metadata structure stored in Supabase
export interface DocumentMetadata {
  size: number;
  filename: string;
  quality_score: number;
  edit_count: number;
  iterations: number;
  created_at: string;
  updated_at: string;
  preview_url?: string;
}

// Type for share links stored in Supabase
export interface ShareLink {
  token: string;
  report_id: string;
  expires_at: string;
  created_at: string;
}

// Create a single instance for the client
const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: !isServer, // Don't persist session on server
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
  global: {
    fetch: (...args) => {
      return fetch(...args);
    },
  },
});

/**
 * Enhanced query function with caching support
 * @param table The table to query
 * @param options The query options
 * @param cacheDuration Cache duration in seconds
 * @returns The query result
 */
export const queryCached = async (table: string, options: any = {}, cacheDuration = CACHE_DURATION.MEDIUM) => {
  // Don't use cache on server
  if (isServer) {
    return await supabase.from(table).select(options.select || '*');
  }

  const cacheKey = `supabase_${table}_${JSON.stringify(options)}`;
  const cachedData = getCachedData(cacheKey);
  
  if (cachedData) {
    return cachedData;
  }

  const result = await supabase.from(table).select(options.select || '*');
  
  if (!result.error && result.data) {
    setCachedData(cacheKey, result, cacheDuration);
  }
  
  return result;
};

/**
 * Get cached data
 * @param key The cache key
 * @returns The cached data or null
 */
const getCachedData = (key: string) => {
  if (isServer) return null;
  
  try {
    const cachedItem = localStorage.getItem(key);
    
    if (!cachedItem) return null;
    
    const { data, expiry } = JSON.parse(cachedItem);
    
    if (Date.now() > expiry) {
      localStorage.removeItem(key);
      return null;
    }
    
    return data;
  } catch (error) {
    console.error('Cache retrieval error:', error);
    return null;
  }
};

/**
 * Set cached data
 * @param key The cache key
 * @param data The data to cache
 * @param duration The cache duration in seconds
 */
const setCachedData = (key: string, data: any, duration: number) => {
  if (isServer) return;
  
  try {
    const item = {
      data,
      expiry: Date.now() + (duration * 1000),
    };
    
    localStorage.setItem(key, JSON.stringify(item));
  } catch (error) {
    console.error('Cache storage error:', error);
  }
};

/**
 * Clear all cached data
 */
export const clearCache = () => {
  if (isServer) return;
  
  try {
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('supabase_')) {
        localStorage.removeItem(key);
      }
    });
  } catch (error) {
    console.error('Cache clearing error:', error);
  }
};

// Document operations
export const documentService = {
  /**
   * Get document metadata from Supabase
   * @param reportId Document ID
   * @returns Document metadata
   */
  async getMetadata(reportId: string): Promise<DocumentMetadata> {
    const { data, error } = await supabase
      .from('documents')
      .select('*')
      .eq('id', reportId)
      .single();
      
    if (error) throw error;
    if (!data) throw new Error('Document not found');
    
    return data as DocumentMetadata;
  },
  
  /**
   * Update document metadata
   * @param reportId Document ID
   * @param metadata Metadata to update
   * @returns Updated document
   */
  async updateMetadata(reportId: string, metadata: Partial<DocumentMetadata>): Promise<DocumentMetadata> {
    const { data, error } = await supabase
      .from('documents')
      .update(metadata)
      .eq('id', reportId)
      .select()
      .single();
      
    if (error) throw error;
    if (!data) throw new Error('Failed to update document');
    
    // Clear any cached data for this document
    if (isBrowser) {
      const cacheKey = `supabase_documents_${JSON.stringify({
        select: '*',
        filter: { id: reportId },
        single: true
      })}`;
      localStorage.removeItem(cacheKey);
    }
    
    return data as DocumentMetadata;
  },
  
  /**
   * Generate a document preview
   * @param reportId Document ID
   * @returns URL to the document preview
   */
  async generatePreview(reportId: string): Promise<string> {
    // First get the document metadata
    const metadata = await this.getMetadata(reportId);
    
    // Check if document has a preview URL already
    if (metadata.preview_url && metadata.preview_url.length > 0) {
      return metadata.preview_url;
    }
    
    // If not, generate a new preview
    const response = await fetch(`${window.location.origin}/api/format/preview-file`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ report_id: reportId })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || 'Failed to generate preview');
    }
    
    const data = await response.json();
    
    if (!data.url) {
      throw new Error('No preview URL returned from server');
    }
    
    // Update the document with the new preview URL
    await this.updateMetadata(reportId, {
      preview_url: data.url
    });
    
    return data.url;
  }
};

// Share links operations
export const shareService = {
  /**
   * Create a new share link in Supabase
   */
  async createShareLink(reportId: string, expirationDays: number = 7): Promise<string> {
    // Calculate expiration date
    const expirationDate = new Date();
    expirationDate.setDate(expirationDate.getDate() + expirationDays);
    
    // Generate a random token
    const token = generateUUID();
    
    // Insert the share link into Supabase
    const { error } = await supabase
      .from('share_links')
      .insert({
        token,
        report_id: reportId,
        expires_at: expirationDate.toISOString(),
        created_at: new Date().toISOString()
      });
    
    if (error) throw new Error(`Error creating share link: ${error.message}`);
    
    // Return the share link with base URL
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || '';
    return `${baseUrl}/shared/${token}`;
  },
  
  /**
   * Get report ID from a share token
   */
  async getReportIdFromToken(token: string): Promise<string | null> {
    const now = new Date().toISOString();
    
    const { data, error } = await supabase
      .from('share_links')
      .select('report_id')
      .eq('token', token)
      .gt('expires_at', now)
      .single();
    
    if (error || !data) return null;
    return data.report_id;
  }
};

export { supabase };
export default supabase; 