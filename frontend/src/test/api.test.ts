import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiRequest, healthCheck } from '../lib/api';

describe('API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('makes API requests with correct headers', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: 'test' }),
    });
    vi.stubGlobal('fetch', mockFetch);

    const result = await apiRequest('/test');
    expect(result).toEqual({ data: 'test' });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/test'),
      expect.objectContaining({
        headers: {
          'Content-Type': 'application/json',
        },
      }),
    );
  });

  it('throws error on failed requests', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: () =>
          Promise.resolve({
            error: { code: 'not_found', message: 'Not found', details: null },
          }),
      }),
    );

    await expect(apiRequest('/not-found')).rejects.toThrow('Not found');
  });

  it('health check returns status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'healthy',
            timestamp: new Date().toISOString(),
          }),
      }),
    );

    const result = await healthCheck();
    expect(result.status).toBe('healthy');
  });
});
