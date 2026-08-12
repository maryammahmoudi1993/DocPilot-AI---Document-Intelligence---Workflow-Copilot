import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Home } from '@/pages/Home';
import { renderWithProviders } from '@/test/testUtils';

const UNSUPPORTED_CLAIM_PATTERNS = [
  /trusted by/i,
  /\d[,.]?\d*\+?\s*(customers|companies|enterprises)/i,
  /\bcertified\b/i,
  /\bSOC ?2\b/i,
  /\d+%\s*(accuracy|faster|time saved)/i,
  /guarantee/i,
];

function renderHome() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Home (landing page)', () => {
  it('renders the hero headline and a CTA that routes to sign-in', () => {
    renderHome();

    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    const ctas = screen.getAllByRole('link', { name: /explore the demo workspace/i });
    expect(ctas.length).toBeGreaterThan(0);
    for (const cta of ctas) {
      expect(cta).toHaveAttribute('href', '/sign-in');
    }
  });

  it('labels itself honestly as a portfolio demonstration', () => {
    renderHome();

    expect(screen.getAllByText(/portfolio demonstration/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/sample data/i).length).toBeGreaterThan(0);
  });

  it('never presents an unsupported marketing claim as verified fact', () => {
    renderHome();

    const bodyText = document.body.textContent ?? '';
    for (const pattern of UNSUPPORTED_CLAIM_PATTERNS) {
      expect(bodyText).not.toMatch(pattern);
    }
  });
});
