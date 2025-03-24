import { DocumentMetadata } from '../types/document';
import { isBrowser, isServer } from '../utils/environment';

export class DocumentService {
  private static instance: DocumentService;

  private constructor() {}

  static getInstance(): DocumentService {
    // In server context, always create a new instance to avoid shared state between requests
    if (isServer) {
      return new DocumentService();
    }
    
    // In browser, use singleton pattern
    if (!DocumentService.instance) {
      DocumentService.instance = new DocumentService();
    }
    return DocumentService.instance;
  }

  async getMetadata(reportId: string): Promise<DocumentMetadata> {
    try {
      const response = await fetch(`/api/documents/${reportId}/metadata`);
      if (!response.ok) {
        throw new Error(`Failed to fetch document metadata: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching document metadata:', error);
      throw new Error('Failed to fetch document metadata');
    }
  }

  async updateMetadata(reportId: string, metadata: Partial<DocumentMetadata>): Promise<DocumentMetadata> {
    try {
      const response = await fetch(`/api/documents/${reportId}/metadata`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(metadata),
      });
      if (!response.ok) {
        throw new Error(`Failed to update document metadata: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error updating document metadata:', error);
      throw new Error('Failed to update document metadata');
    }
  }

  async generatePreview(reportId: string): Promise<string> {
    try {
      const response = await fetch(`/api/documents/${reportId}/preview`);
      if (!response.ok) {
        throw new Error(`Failed to generate preview: ${response.statusText}`);
      }
      const data = await response.json();
      return data.url;
    } catch (error) {
      console.error('Error generating preview:', error);
      throw new Error('Failed to generate document preview');
    }
  }

  async updateDownloadCount(reportId: string): Promise<void> {
    try {
      const metadata = await this.getMetadata(reportId);
      await this.updateMetadata(reportId, {
        download_count: (metadata.download_count || 0) + 1,
        last_downloaded_at: new Date().toISOString(),
      });
    } catch (error) {
      console.error('Error updating download count:', error);
      // Non-critical operation, don't throw to avoid breaking download flow
    }
  }
} 