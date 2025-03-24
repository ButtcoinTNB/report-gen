import { DocumentMetadata } from '../types/document';

export class DocumentService {
  private static instance: DocumentService;

  private constructor() {}

  static getInstance(): DocumentService {
    if (!DocumentService.instance) {
      DocumentService.instance = new DocumentService();
    }
    return DocumentService.instance;
  }

  async getMetadata(reportId: string): Promise<DocumentMetadata> {
    const response = await fetch(`/api/documents/${reportId}/metadata`);
    if (!response.ok) {
      throw new Error('Failed to fetch document metadata');
    }
    return response.json();
  }

  async updateMetadata(reportId: string, metadata: Partial<DocumentMetadata>): Promise<DocumentMetadata> {
    const response = await fetch(`/api/documents/${reportId}/metadata`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(metadata),
    });
    if (!response.ok) {
      throw new Error('Failed to update document metadata');
    }
    return response.json();
  }

  async generatePreview(reportId: string): Promise<string> {
    const response = await fetch(`/api/documents/${reportId}/preview`);
    if (!response.ok) {
      throw new Error('Failed to generate preview');
    }
    const data = await response.json();
    return data.url;
  }

  async updateDownloadCount(reportId: string): Promise<void> {
    const metadata = await this.getMetadata(reportId);
    await this.updateMetadata(reportId, {
      download_count: (metadata.download_count || 0) + 1,
      last_downloaded_at: new Date().toISOString(),
    });
  }
} 