import axios from 'axios';
import apiClient from './api';
import { ProcessStage } from '../context/TaskContext';

export interface CreateVersionRequest {
  label: string;
  description?: string;
  stage: ProcessStage;
}

export interface CreateVersionResponse {
  id: string;
  url?: string;
  createdAt: string;
}

export interface CompareVersionsResponse {
  diff: string;
  changes: Array<{
    type: 'addition' | 'deletion' | 'modification';
    section: string;
    content: string;
  }>;
}

export interface GetReportResponse {
  id: string;
  title: string;
  content: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  versions?: Array<{
    id: string;
    label: string;
    createdAt: string;
    isCurrent: boolean;
  }>;
}

class ReportService {
  /**
   * Create a new report
   */
  async createReport(files: string[]): Promise<string> {
    try {
      const response = await apiClient.post<{ id: string }>('/api/reports', { files });
      return response?.data?.id || '';
    } catch (error) {
      console.error('Failed to create report:', error);
      throw error;
    }
  }

  /**
   * Get a report by ID
   */
  async getReport(reportId: string): Promise<GetReportResponse> {
    try {
      const response = await apiClient.get<GetReportResponse>(`/api/reports/${reportId}`);
      if (!response || !response.data) {
        throw new Error('Invalid response from API');
      }
      return response.data;
    } catch (error) {
      console.error(`Failed to get report ${reportId}:`, error);
      throw error;
    }
  }

  /**
   * Create a new version of a report
   */
  async createVersion(
    reportId: string,
    versionData: CreateVersionRequest
  ): Promise<CreateVersionResponse> {
    try {
      const response = await apiClient.post<CreateVersionResponse>(
        `/api/reports/${reportId}/versions`,
        versionData
      );
      if (!response || !response.data) {
        throw new Error('Invalid response from API');
      }
      return response.data;
    } catch (error) {
      console.error(`Failed to create version for report ${reportId}:`, error);
      throw error;
    }
  }

  /**
   * Get a specific version of a report
   */
  async getVersion(versionId: string): Promise<{ content: string; metadata: any }> {
    try {
      const response = await apiClient.get<{ content: string; metadata: any }>(
        `/api/versions/${versionId}`
      );
      if (!response || !response.data) {
        throw new Error('Invalid response from API');
      }
      return response.data;
    } catch (error) {
      console.error(`Failed to get version ${versionId}:`, error);
      throw error;
    }
  }

  /**
   * Compare two versions of a report
   */
  async compareVersions(versionId1: string, versionId2: string): Promise<CompareVersionsResponse> {
    try {
      const response = await apiClient.get<CompareVersionsResponse>(`/api/versions/compare`, {
        params: { v1: versionId1, v2: versionId2 }
      });
      if (!response || !response.data) {
        throw new Error('Invalid response from API');
      }
      return response.data;
    } catch (error) {
      console.error(`Failed to compare versions ${versionId1} and ${versionId2}:`, error);
      throw error;
    }
  }

  /**
   * Download a specific version
   */
  async downloadVersion(versionId: string, filename?: string): Promise<void> {
    try {
      const response = await apiClient.get<{ url: string }>(`/api/versions/${versionId}/download`);
      if (!response || !response.data || !response.data.url) {
        throw new Error('Invalid download URL received from API');
      }
      await apiClient.downloadFile(response.data.url, filename || `report-${versionId}.docx`);
    } catch (error) {
      console.error(`Failed to download version ${versionId}:`, error);
      throw error;
    }
  }

  /**
   * Refine a report with new instructions
   */
  async refineReport(
    reportId: string,
    instructions: string
  ): Promise<{ taskId: string }> {
    try {
      const response = await apiClient.post<{ taskId: string }>(
        `/api/reports/${reportId}/refine`,
        { instructions }
      );
      if (!response || !response.data) {
        throw new Error('Invalid response from API');
      }
      return response.data;
    } catch (error) {
      console.error(`Failed to refine report ${reportId}:`, error);
      throw error;
    }
  }

  /**
   * Get report generation task status
   */
  async getTaskStatus(taskId: string): Promise<{
    id: string;
    status: string;
    progress: number;
    stage: string;
    message: string;
  }> {
    try {
      const response = await apiClient.get<{
        id: string;
        status: string;
        progress: number;
        stage: string;
        message: string;
      }>(`/api/tasks/${taskId}`);
      if (!response || !response.data) {
        throw new Error('Invalid response from API');
      }
      return response.data;
    } catch (error) {
      console.error(`Failed to get task status ${taskId}:`, error);
      throw error;
    }
  }
}

export const reportService = new ReportService();
export default reportService; 