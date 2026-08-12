import { NODE_CATALOG } from './nodeCatalog';
import type { NodeKind } from '@/features/workflows/types';

export interface NodePaletteProps {
  onAdd: (kind: NodeKind) => void;
}

const SECTION_LABEL: Record<string, string> = {
  trigger: 'Triggers',
  condition: 'Conditions',
  action: 'Actions',
};

/** Draggable (and, for keyboard/no-drag use, clickable) node library.
 * Dragging onto the canvas is handled by WorkflowCanvas's onDrop;
 * clicking a palette entry adds the node at a default position
 * instead, which is what makes the whole builder usable without a
 * pointer. */
export function NodePalette({ onAdd }: NodePaletteProps) {
  const sections = ['trigger', 'condition', 'action'] as const;

  return (
    <div className="w-56 shrink-0 space-y-4 overflow-y-auto border-r border-border bg-sidebar p-3">
      {sections.map((section) => (
        <div key={section}>
          <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-text-muted">
            {SECTION_LABEL[section]}
          </h3>
          <div className="space-y-1">
            {NODE_CATALOG.filter((entry) => entry.nodeType === section).map((entry) => (
              <button
                key={entry.kind}
                type="button"
                draggable
                onDragStart={(event) => {
                  event.dataTransfer.setData('application/docpilot-node-kind', entry.kind);
                  event.dataTransfer.effectAllowed = 'move';
                }}
                onClick={() => onAdd(entry.kind)}
                title={entry.description}
                className="flex w-full items-center gap-2 rounded-md border border-border bg-card px-2.5 py-2 text-left text-xs text-text-primary transition-colors duration-fast hover:bg-lavender focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <entry.icon className="size-4 shrink-0 text-primary" aria-hidden="true" />
                {entry.label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
