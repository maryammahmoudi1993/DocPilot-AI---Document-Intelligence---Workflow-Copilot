import { describe, it, expect } from 'vitest';
import { config } from '../config';

describe('Configuration', () => {
  it('has required configuration properties', () => {
    expect(config).toHaveProperty('apiBaseUrl');
    expect(config).toHaveProperty('appName');
    expect(config).toHaveProperty('environment');
  });

  it('has a valid API base URL', () => {
    expect(config.apiBaseUrl).toBeTruthy();
    expect(typeof config.apiBaseUrl).toBe('string');
  });
});
