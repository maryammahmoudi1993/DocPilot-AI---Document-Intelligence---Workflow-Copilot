export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';
export type RiskLevel = 'low' | 'medium' | 'high';

export interface ApprovalComment {
  id: string;
  author_email: string | null;
  body: string;
  created_at: string;
}

export interface ApprovalRequest {
  id: string;
  title: string;
  description: string;
  risk_level: RiskLevel;
  status: ApprovalStatus;
  assigned_role: string;
  document_id: string | null;
  requested_by_email: string | null;
  decided_by_email: string | null;
  decided_at: string | null;
  expires_at: string | null;
  comments: ApprovalComment[];
  created_at: string;
  updated_at: string;
}

export interface ApprovalDecisionRequest {
  status: 'approved' | 'rejected';
  reason?: string;
}
