import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('Accessibility', () => {
  it('has proper heading structure', () => {
    render(<App />);
    const headings = screen.getAllByRole('heading');
    expect(headings.length).toBeGreaterThan(0);
  });

  it('has proper landmark regions', () => {
    render(<App />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
