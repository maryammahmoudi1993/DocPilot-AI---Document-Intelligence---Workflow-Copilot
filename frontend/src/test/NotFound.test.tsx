import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('Not Found Route', () => {
  it('displays 404 page for unknown routes', () => {
    window.history.pushState({}, '', '/unknown-route');
    render(<App />);
    expect(screen.getByText('404')).toBeInTheDocument();
    expect(screen.getByText('Page not found')).toBeInTheDocument();
  });
});
