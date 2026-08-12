import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { notificationHandlers, demoNotifications } from '@/mocks/notificationHandlers';
import { NotificationsMenu } from '@/components/layout/NotificationsMenu';
import { renderWithProviders } from '@/test/testUtils';

beforeEach(() => {
  demoNotifications[0]!.is_read = false;
  server.use(...signedInHandlers, ...notificationHandlers);
});

describe('NotificationsMenu', () => {
  it('shows an unread count badge', async () => {
    renderWithProviders(<NotificationsMenu />);

    expect(
      await screen.findByRole('button', { name: /notifications \(1 unread\)/i }),
    ).toBeInTheDocument();
  });

  it('opens the menu and lists notifications', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationsMenu />);
    await screen.findByRole('button', { name: /notifications/i });

    await user.click(screen.getByRole('button', { name: /notifications/i }));

    expect(await screen.findByText('Approval requested')).toBeInTheDocument();
    expect(screen.getByText('Document processed')).toBeInTheDocument();
  });

  it('marks an unread notification as read on click', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationsMenu />);
    await user.click(await screen.findByRole('button', { name: /notifications/i }));
    await user.click(await screen.findByText('Approval requested'));

    await waitFor(() => expect(demoNotifications[0]!.is_read).toBe(true));
  });

  it('closes the menu on Escape', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationsMenu />);
    await user.click(await screen.findByRole('button', { name: /notifications/i }));
    expect(await screen.findByRole('menu')).toBeInTheDocument();

    await user.keyboard('{Escape}');

    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
  });
});
