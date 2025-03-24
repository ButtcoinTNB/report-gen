import axios, { AxiosInstance } from 'axios';

export class ApiService {
  protected client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: '/',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for auth token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }
} 