export interface WorkspaceSettings {
  notify_on_approval_requested: boolean;
  notify_on_document_processed: boolean;
  webhook_notifications_enabled: boolean;
  auto_classify_enabled: boolean;
  document_retention_days: number | null;
  raw_text_retention_days: number | null;
  updated_at: string;
}

export type WorkspaceSettingsUpdate = Partial<
  Omit<WorkspaceSettings, 'updated_at'>
>;
