/** Mirrors backend/apps/workflows/models.py and serializers.py exactly. */

export type NodeType = 'trigger' | 'condition' | 'action';

export type TriggerKind = 'document_uploaded' | 'document_approved';
export type ConditionKind = 'total_greater_than_threshold' | 'confidence_below_threshold';
export type ActionKind =
  | 'request_approval'
  | 'send_notification'
  | 'trigger_webhook'
  | 'add_tag'
  | 'export_structured_data';

export type NodeKind = TriggerKind | ConditionKind | ActionKind;

export interface WorkflowNodeData {
  node_key: string;
  node_type: NodeType;
  kind: NodeKind;
  config: Record<string, unknown>;
  position: { x: number; y: number };
}

export interface WorkflowEdgeData {
  source_node_key: string;
  target_node_key: string;
  branch: '' | 'true' | 'false';
}

export type WorkflowVersionStatus = 'draft' | 'active' | 'archived';

export interface WorkflowVersion {
  id: string;
  version_number: number;
  status: WorkflowVersionStatus;
  nodes: WorkflowNodeData[];
  edges: WorkflowEdgeData[];
  created_at: string;
  activated_at: string | null;
  // Only present on the response to a draft save (PUT .../draft/), not
  // on GET responses that embed a version — see WorkflowDraftView.
  validation_errors?: string[];
}

export type WorkflowVersionWithValidation = WorkflowVersion;

export interface Workflow {
  id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends Workflow {
  active_version: WorkflowVersion | null;
  draft_version: WorkflowVersion | null;
}

export interface WorkflowStepRun {
  id: string;
  node_key: string;
  node_kind: string;
  status: 'succeeded' | 'failed' | 'skipped';
  output: Record<string, unknown>;
  error_code: string;
  attempt_count: number;
  started_at: string;
  completed_at: string | null;
}

export interface WorkflowRun {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  trigger_context: Record<string, unknown>;
  is_test_run: boolean;
  error_code: string;
  step_runs: WorkflowStepRun[];
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface SaveDraftRequest {
  nodes: WorkflowNodeData[];
  edges: WorkflowEdgeData[];
}
