import { Bell, CheckCircle2, FileUp, Percent, Send, Tag, Upload, Webhook } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { NodeKind, NodeType } from '@/features/workflows/types';

export interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'number' | 'textarea';
  placeholder?: string;
}

export interface NodeCatalogEntry {
  kind: NodeKind;
  nodeType: NodeType;
  label: string;
  description: string;
  icon: LucideIcon;
  configFields: ConfigField[];
}

/** The complete, fixed node library this phase implements — drives the
 * palette, the canvas node renderer, and the settings panel form. Any
 * kind not listed here cannot be added from the UI (the backend's
 * validate_graph is the actual source of truth on what's a legal
 * kind — this catalog exists only to drive the builder UI). */
export const NODE_CATALOG: NodeCatalogEntry[] = [
  {
    kind: 'document_uploaded',
    nodeType: 'trigger',
    label: 'Document uploaded',
    description: 'Starts when a document is uploaded to this workspace.',
    icon: Upload,
    configFields: [],
  },
  {
    kind: 'document_approved',
    nodeType: 'trigger',
    label: 'Document approved',
    description: 'Starts when an invoice extraction is approved.',
    icon: CheckCircle2,
    configFields: [],
  },
  {
    kind: 'total_greater_than_threshold',
    nodeType: 'condition',
    label: 'Total greater than',
    description: 'Branches on whether the invoice total exceeds a threshold.',
    icon: FileUp,
    configFields: [{ key: 'threshold', label: 'Threshold', type: 'number', placeholder: '1000' }],
  },
  {
    kind: 'confidence_below_threshold',
    nodeType: 'condition',
    label: 'Confidence below',
    description: 'Branches on whether extraction confidence is below a threshold.',
    icon: Percent,
    configFields: [{ key: 'threshold', label: 'Threshold (0–1)', type: 'number', placeholder: '0.6' }],
  },
  {
    kind: 'request_approval',
    nodeType: 'action',
    label: 'Request approval',
    description: 'Requests approval from a workspace role.',
    icon: CheckCircle2,
    configFields: [
      { key: 'approver_role', label: 'Approver role', type: 'text', placeholder: 'admin' },
    ],
  },
  {
    kind: 'send_notification',
    nodeType: 'action',
    label: 'Send notification',
    description: 'Sends a notification message. Retried on provider failure.',
    icon: Bell,
    configFields: [
      { key: 'message', label: 'Message', type: 'textarea', placeholder: 'A document needs review.' },
      { key: 'recipient', label: 'Recipient', type: 'text', placeholder: 'workspace' },
    ],
  },
  {
    kind: 'trigger_webhook',
    nodeType: 'action',
    label: 'Trigger webhook',
    description: 'Calls an external URL. Retried on provider failure.',
    icon: Webhook,
    configFields: [{ key: 'url', label: 'Webhook URL', type: 'text', placeholder: 'https://example.com/hook' }],
  },
  {
    kind: 'add_tag',
    nodeType: 'action',
    label: 'Add tag',
    description: 'Tags the document.',
    icon: Tag,
    configFields: [{ key: 'tag', label: 'Tag', type: 'text', placeholder: 'needs-review' }],
  },
  {
    kind: 'export_structured_data',
    nodeType: 'action',
    label: 'Export structured data',
    description: 'Exports the extracted fields in a chosen format.',
    icon: Send,
    configFields: [{ key: 'format', label: 'Format', type: 'text', placeholder: 'json' }],
  },
];

export const NODE_CATALOG_BY_KIND: Record<string, NodeCatalogEntry> = Object.fromEntries(
  NODE_CATALOG.map((entry) => [entry.kind, entry]),
);
