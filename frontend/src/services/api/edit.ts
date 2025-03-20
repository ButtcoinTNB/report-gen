import { corsHelper } from '../../utils/corsHelper';
import { 
  Report, 
  ReportCamel, 
  EditReportResponse,
  EditReportResponseCamel, 
  adaptEditReportResponse 
} from '../../types';
import { adaptApiResponse, adaptApiRequest } from '../../utils/adapters';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const editApi = {
  editReport: async (reportId: string, instructions: string): Promise<EditReportResponseCamel> => {
    // Prepare the request body using the adapter
    const requestBody = adaptApiRequest({
      reportId,
      instructions
    });

    const response = await corsHelper.fetch(`${BASE_URL}/api/generate/refine`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      throw new Error(`Failed to edit report: ${response.statusText}`);
    }

    // Convert the snake_case response to camelCase
    const data = await response.json();
    return adaptEditReportResponse(data);
  }
}; 