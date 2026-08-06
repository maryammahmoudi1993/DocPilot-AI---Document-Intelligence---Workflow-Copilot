import { useState } from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Dialog } from '@/components/ui/Dialog';

function DialogHarness() {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button onClick={() => setOpen(true)}>Open dialog</button>
      <Dialog open={open} onOpenChange={setOpen} title="Confirm" description="Are you sure?">
        <button>Inside dialog</button>
      </Dialog>
    </div>
  );
}

describe('Dialog', () => {
  it('traps focus inside the dialog while open', async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);

    await user.click(screen.getByRole('button', { name: 'Open dialog' }));
    expect(await screen.findByRole('dialog', { name: 'Confirm' })).toBeInTheDocument();

    // Tabbing repeatedly must never move focus outside the dialog.
    for (let i = 0; i < 5; i++) {
      await user.tab();
      expect(screen.getByRole('dialog')).toContainElement(document.activeElement as HTMLElement);
    }
  });

  it('restores focus to the trigger when closed', async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);

    const trigger = screen.getByRole('button', { name: 'Open dialog' });
    await user.click(trigger);
    await screen.findByRole('dialog');

    await user.keyboard('{Escape}');

    await waitFor(() => expect(trigger).toHaveFocus(), { timeout: 3000 });
  });
});
