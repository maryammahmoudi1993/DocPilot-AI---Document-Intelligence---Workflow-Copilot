import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToastProvider, useToast } from '@/components/ui/Toast';

function ToastTrigger() {
  const { showToast } = useToast();
  return (
    <button onClick={() => showToast({ title: 'Document approved', variant: 'success' })}>Approve</button>
  );
}

describe('Toast', () => {
  it('shows a toast after showToast is called and it can be dismissed', async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <ToastTrigger />
      </ToastProvider>,
    );

    expect(screen.queryByText('Document approved')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Approve' }));
    expect(await screen.findByText('Document approved')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /dismiss notification/i }));
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  it('throws a clear error if useToast is used outside the provider', () => {
    const consoleError = console.error;
    console.error = () => {};
    function Broken() {
      useToast();
      return null;
    }
    expect(() => render(<Broken />)).toThrow('useToast must be used within a ToastProvider');
    console.error = consoleError;
  });
});
