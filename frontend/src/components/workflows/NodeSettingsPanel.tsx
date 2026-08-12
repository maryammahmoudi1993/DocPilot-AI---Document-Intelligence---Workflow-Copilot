import { X } from 'lucide-react';
import { NODE_CATALOG_BY_KIND } from './nodeCatalog';
import type { WorkflowNodeData } from '@/features/workflows/types';
import { Input } from '@/components/ui/Input';
import { IconButton } from '@/components/ui/IconButton';
import { Button } from '@/components/ui/Button';

export interface NodeSettingsPanelProps {
  node: WorkflowNodeData;
  isEditable: boolean;
  onChange: (config: Record<string, unknown>) => void;
  onDelete: () => void;
  onClose: () => void;
}

/** Config form for the selected node — the accessible, keyboard-
 * operable alternative to configuring a node visually on the canvas
 * (every field here is a plain labeled input, reachable by Tab). */
export function NodeSettingsPanel({ node, isEditable, onChange, onDelete, onClose }: NodeSettingsPanelProps) {
  const entry = NODE_CATALOG_BY_KIND[node.kind];

  return (
    <div className="flex h-full w-72 shrink-0 flex-col border-l border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-3 py-2.5">
        <h2 className="text-sm font-semibold text-text-primary">{entry?.label ?? node.kind}</h2>
        <IconButton aria-label="Close node settings" onClick={onClose}>
          <X className="size-4" />
        </IconButton>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-3">
        <p className="text-xs text-text-secondary">{entry?.description}</p>
        {entry?.configFields.length === 0 && (
          <p className="text-xs text-text-muted">This node has no configuration.</p>
        )}
        {entry?.configFields.map((field) => (
          <label key={field.key} className="block space-y-1 text-xs">
            <span className="font-medium text-text-primary">{field.label}</span>
            <Input
              type={field.type === 'number' ? 'number' : 'text'}
              value={String(node.config[field.key] ?? '')}
              placeholder={field.placeholder}
              disabled={!isEditable}
              onChange={(event) => {
                const raw = event.target.value;
                onChange({
                  ...node.config,
                  [field.key]: field.type === 'number' && raw !== '' ? Number(raw) : raw,
                });
              }}
            />
          </label>
        ))}
      </div>
      {isEditable && (
        <div className="border-t border-border p-3">
          <Button type="button" variant="destructive" size="sm" className="w-full" onClick={onDelete}>
            Delete node
          </Button>
        </div>
      )}
    </div>
  );
}
