import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge';

describe('StatusBadge', () => {
  it.each([
    ['processing', 'Processing'],
    ['approved', 'Approved'],
    ['needs_review', 'Needs Review'],
    ['failed', 'Failed'],
  ] as const)('renders the %s status as "%s"', (status, label) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});

describe('ConfidenceBadge', () => {
  it('buckets a high score', () => {
    render(<ConfidenceBadge score={0.95} />);
    expect(screen.getByText('High · 95%')).toBeInTheDocument();
  });

  it('buckets a medium score', () => {
    render(<ConfidenceBadge score={0.7} />);
    expect(screen.getByText('Medium · 70%')).toBeInTheDocument();
  });

  it('buckets a low score', () => {
    render(<ConfidenceBadge score={0.2} />);
    expect(screen.getByText('Low · 20%')).toBeInTheDocument();
  });

  it('clamps out-of-range scores instead of rendering nonsense', () => {
    render(<ConfidenceBadge score={1.5} />);
    expect(screen.getByText('High · 100%')).toBeInTheDocument();
  });
});
