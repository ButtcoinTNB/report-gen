import { SHARE } from '../constants/app';
import { retryWithBackoff } from '../utils/common';
import { supabase } from '../utils/supabase';

export interface ShareLinkData {
  url: string;
  expiresAt: Date;
  remainingDownloads: number;
  documentId: string;
}

export class ShareService {
  private static instance: ShareService;

  private constructor() {}

  static getInstance(): ShareService {
    if (!ShareService.instance) {
      ShareService.instance = new ShareService();
    }
    return ShareService.instance;
  }

  async createShareLink(documentId: string): Promise<ShareLinkData> {
    try {
      const response = await retryWithBackoff(() =>
        fetch('/api/share/create', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            documentId,
            expiresIn: SHARE.LINK_EXPIRATION,
            maxDownloads: SHARE.MAX_DOWNLOADS,
          }),
        })
      );

      if (!response.ok) {
        throw new Error('Failed to create share link');
      }

      const data = await response.json();
      return {
        url: data.url,
        expiresAt: new Date(data.expiresAt),
        remainingDownloads: data.remainingDownloads,
        documentId: data.documentId,
      };
    } catch (error) {
      console.error('Error creating share link:', error);
      throw error;
    }
  }

  async getShareLinkInfo(token: string): Promise<ShareLinkData> {
    try {
      const response = await retryWithBackoff(() =>
        fetch(`/api/share/${token}`)
      );

      if (!response.ok) {
        throw new Error('Failed to get share link info');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting share link info:', error);
      throw error;
    }
  }

  async revokeShareLink(token: string): Promise<void> {
    try {
      const response = await retryWithBackoff(() =>
        fetch(`/api/share/${token}`, {
          method: 'DELETE',
        })
      );

      if (!response.ok) {
        throw new Error('Failed to revoke share link');
      }
    } catch (error) {
      console.error('Error revoking share link:', error);
      throw error;
    }
  }

  async trackDownload(token: string): Promise<void> {
    try {
      const response = await retryWithBackoff(() =>
        fetch(`/api/share/${token}/download`, {
          method: 'POST',
        })
      );

      if (!response.ok) {
        throw new Error('Failed to track download');
      }
    } catch (error) {
      console.error('Error tracking download:', error);
      throw error;
    }
  }
} 