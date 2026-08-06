export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  appName: 'DocPilot AI',
  environment: import.meta.env.MODE || 'development',
} as const;
