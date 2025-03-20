/**
 * Helper for handling cross-origin requests with proper credentials and CORS handling
 */
export const corsHelper = {
  /**
   * Fetch wrapper that handles CORS correctly
   * @param url The URL to fetch
   * @param options Fetch options
   * @returns A promise resolving to the fetch response
   */
  fetch: async (url: string, options: RequestInit = {}): Promise<Response> => {
    // Ensure credentials are included
    const corsOptions: RequestInit = {
      ...options,
      credentials: 'include',
      headers: {
        ...options.headers,
        'Accept': 'application/json',
      }
    };

    return fetch(url, corsOptions);
  }
}; 