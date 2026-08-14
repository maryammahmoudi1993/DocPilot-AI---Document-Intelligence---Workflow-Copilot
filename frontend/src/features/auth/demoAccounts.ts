/** The five demo-workspace accounts `seed_demo_data` creates on the
 * backend (backend/apps/accounts/management/commands/seed_demo_data.py)
 * — one per workspace role, used by SignInPage's quick-login buttons so
 * a prospective client/employer can see every permission level without
 * typing credentials. The password is the same intentionally-public
 * portfolio-demo credential documented in the root README — not a real
 * secret, and only ever valid against the seeded demo workspace.
 */
export interface DemoAccount {
  role: string;
  label: string;
  email: string;
  description: string;
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    role: 'owner',
    label: 'Owner',
    email: 'owner@demo.docpilot.ai',
    description: 'Full workspace access, including settings and billing-adjacent screens.',
  },
  {
    role: 'admin',
    label: 'Admin',
    email: 'admin@demo.docpilot.ai',
    description: 'Manages members and integrations; no ownership transfer.',
  },
  {
    role: 'finance_manager',
    label: 'Finance Manager',
    email: 'finance@demo.docpilot.ai',
    description: 'Reviews and approves high-value documents.',
  },
  {
    role: 'reviewer',
    label: 'Reviewer',
    email: 'reviewer@demo.docpilot.ai',
    description: 'Corrects low-confidence extraction fields in the review queue.',
  },
  {
    role: 'viewer',
    label: 'Viewer',
    email: 'viewer@demo.docpilot.ai',
    description: 'Read-only access — the most restricted role.',
  },
];

export const DEMO_ACCOUNT_PASSWORD = 'DemoWorkspace!2026';
