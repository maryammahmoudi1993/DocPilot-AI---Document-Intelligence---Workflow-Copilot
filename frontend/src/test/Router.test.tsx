import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('Router', () => {
  it('renders the home route', () => {
    render(<App />);
    expect(screen.getByText('DocPilot AI')).toBeInTheDocument();
  });
});
