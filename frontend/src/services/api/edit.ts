import { corsHelper } from '../../utils/corsHelper';
import { Report } from '../../types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const editApi = {
  editReport: async (reportId: string, instructions: string): Promise<Report> => {
    const response = await corsHelper.fetch(`${BASE_URL}/api/generate/refine`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        report_id: reportId,
        instructions
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to edit report: ${response.statusText}`);
    }

    return response.json();
  }
}; 