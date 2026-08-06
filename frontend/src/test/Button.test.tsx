import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';

describe('Button', () => {
  it('renders each variant with its own class', () => {
    const { rerender } = render(<Button variant="primary">Go</Button>);
    expect(screen.getByRole('button', { name: 'Go' })).toHaveClass('bg-primary');

    rerender(<Button variant="destructive">Delete</Button>);
    expect(screen.getByRole('button', { name: 'Delete' })).toHaveClass('bg-status-failed');
  });

  it('is disabled and inert while loading', async () => {
    const onClick = vi.fn();
    render(
      <Button isLoading onClick={onClick}>
        Save
      </Button>,
    );
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');

    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('respects an explicit disabled prop', () => {
    render(<Button disabled>Submit</Button>);
    expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled();
  });
});

describe('IconButton', () => {
  it('requires and renders an accessible name', () => {
    render(
      <IconButton aria-label="Collapse sidebar">
        <span aria-hidden="true">«</span>
      </IconButton>,
    );
    expect(screen.getByRole('button', { name: 'Collapse sidebar' })).toBeInTheDocument();
  });
});
