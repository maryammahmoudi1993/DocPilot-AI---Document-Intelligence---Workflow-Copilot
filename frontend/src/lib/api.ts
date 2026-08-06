import { config } from '../config';

export interface ApiError {
  error: {
    code: string;
    message: string;
    details: unknown;
  };
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${config.apiBaseUrl}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.error.message || 'API request failed');
  }

  return response.json();
}

export async function healthCheck(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health/');
}
