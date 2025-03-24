export interface DocumentMetadata {
  id: string;
  filename: string;
  size: number;
  content_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  quality_score: number;
  edit_count: number;
  iterations: number;
  time_saved: number;
  pages: number;
  download_count: number;
  last_downloaded_at?: string;
  created_at: string;
  updated_at: string;
} 