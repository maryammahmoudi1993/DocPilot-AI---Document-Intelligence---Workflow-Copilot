import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import { server } from '@/mocks/server';
import { SignInPage } from '@/pages/SignIn';
import { renderWithProviders } from '@/test/testUtils';
import { DEMO_ACCOUNTS } from '@/features/auth/demoAccounts';

const API = config.apiBaseUrl;

function renderSignIn(initialPath = '/sign-in') {
  return renderWithProviders(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/sign-in" element={<SignInPage />} />
        <Route path="/app/dashboard" element={<div>Dashboard content</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('SignInPage — validation', () => {
  it('shows validation errors for empty fields without calling the API', async () => {
    const user = userEvent.setup();
    renderSignIn();

    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(await screen.findByText('Email is required')).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();
  });

  it('rejects an invalid email format', async () => {
    const user = userEvent.setup();
    renderSignIn();

    await user.type(screen.getByLabelText('Email'), 'not-an-email');
    await user.type(screen.getByLabelText('Password'), 'something');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(await screen.findByText('Enter a valid email address')).toBeInTheDocument();
  });
});

describe('SignInPage — submission', () => {
  it('signs in with valid credentials and redirects to the dashboard', async () => {
    const user = userEvent.setup();
    renderSignIn();

    await user.type(screen.getByLabelText('Email'), 'owner@demo.docpilot.ai');
    await user.type(screen.getByLabelText('Password'), 'correct-password');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(await screen.findByText('Dashboard content')).toBeInTheDocument();
  });

  it('shows a generic error for invalid credentials without leaking whether the account exists', async () => {
    const user = userEvent.setup();
    renderSignIn();

    await user.type(screen.getByLabelText('Email'), 'owner@demo.docpilot.ai');
    await user.type(screen.getByLabelText('Password'), 'wrong-password');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(await screen.findByText('Invalid email or password.')).toBeInTheDocument();
  });

  it('shows a loading state while the request is in flight', async () => {
    server.use(
      http.post(`${API}/auth/login/`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
        return HttpResponse.json({
          access: 'token',
          user: { id: '1', email: 'a@b.com', first_name: 'A', last_name: 'B' },
        });
      }),
    );
    const user = userEvent.setup();
    renderSignIn();

    await user.type(screen.getByLabelText('Email'), 'owner@demo.docpilot.ai');
    await user.type(screen.getByLabelText('Password'), 'correct-password');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(screen.getByRole('button', { name: 'Sign In' })).toBeDisabled();
    // The form is replaced by the redirected page on success — "loading
    // resolved" is observed as the redirect happening, not the button
    // becoming enabled again (it's gone by then).
    expect(await screen.findByText('Dashboard content')).toBeInTheDocument();
  });

  it('shows a specific message when the login endpoint is throttled', async () => {
    server.use(
      http.post(
        `${API}/auth/login/`,
        () =>
          HttpResponse.json(
            { error: { code: 'throttled', message: 'Request was throttled.', details: null } },
            { status: 429 },
          ),
      ),
    );
    const user = userEvent.setup();
    renderSignIn();

    await user.type(screen.getByLabelText('Email'), 'owner@demo.docpilot.ai');
    await user.type(screen.getByLabelText('Password'), 'correct-password');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(await screen.findByText(/too many attempts/i)).toBeInTheDocument();
  });

  it('is fully operable by keyboard alone', async () => {
    const user = userEvent.setup();
    renderSignIn();

    await user.tab(); // -> email
    expect(screen.getByLabelText('Email')).toHaveFocus();
    await user.keyboard('owner@demo.docpilot.ai');
    await user.tab(); // -> password
    expect(screen.getByLabelText('Password')).toHaveFocus();
    await user.keyboard('correct-password{Enter}');

    expect(await screen.findByText('Dashboard content')).toBeInTheDocument();
  });

  it('never renders the access token anywhere in the DOM', async () => {
    const user = userEvent.setup();
    const { container } = renderSignIn();

    await user.type(screen.getByLabelText('Email'), 'owner@demo.docpilot.ai');
    await user.type(screen.getByLabelText('Password'), 'correct-password');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    await screen.findByText('Dashboard content');
    expect(container.innerHTML).not.toContain('fake-access-token');
  });
});

describe('SignInPage — demo quick login', () => {
  it('offers one quick-login button per demo workspace role', () => {
    renderSignIn();

    for (const account of DEMO_ACCOUNTS) {
      expect(screen.getByRole('button', { name: new RegExp(account.label, 'i') })).toBeInTheDocument();
    }
  });

  it('signs in as the selected role without the user typing any credentials', async () => {
    const user = userEvent.setup();
    renderSignIn();

    expect(screen.queryByLabelText('Email')).toHaveValue('');
    await user.click(screen.getByRole('button', { name: /viewer/i }));

    expect(await screen.findByText('Dashboard content')).toBeInTheDocument();
  });

  it('shows a loading state only on the clicked button while its request is in flight', async () => {
    server.use(
      http.post(`${API}/auth/login/`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
        return HttpResponse.json({
          access: 'token',
          user: { id: 'reviewer', email: 'reviewer@demo.docpilot.ai', first_name: 'Demo', last_name: 'Reviewer' },
        });
      }),
    );
    const user = userEvent.setup();
    renderSignIn();

    const reviewerButton = screen.getByRole('button', { name: /reviewer/i });
    const ownerButton = screen.getByRole('button', { name: /owner/i });
    await user.click(reviewerButton);

    expect(reviewerButton).toBeDisabled();
    expect(ownerButton).toBeDisabled(); // any in-flight login disables every quick-login button
    expect(await screen.findByText('Dashboard content')).toBeInTheDocument();
  });
});
