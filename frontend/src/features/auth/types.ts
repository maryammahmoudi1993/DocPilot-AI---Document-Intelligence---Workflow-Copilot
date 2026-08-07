export type WorkspaceRole = 'owner' | 'admin' | 'finance_manager' | 'reviewer' | 'viewer';

export const MANAGER_ROLES: WorkspaceRole[] = ['owner', 'admin'];

export interface AuthUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  slug: string;
  role: WorkspaceRole;
}

export interface SessionResponse {
  user: AuthUser;
  workspaces: WorkspaceSummary[];
  active_workspace_id: string | null;
}

export interface LoginResponse {
  access: string;
  user: AuthUser;
}
