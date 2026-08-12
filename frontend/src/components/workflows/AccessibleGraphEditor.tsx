import { Trash2 } from 'lucide-react';
import { NODE_CATALOG, NODE_CATALOG_BY_KIND } from './nodeCatalog';
import type { NodeKind, WorkflowEdgeData, WorkflowNodeData } from '@/features/workflows/types';
import { Button } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';

const nativeSelectClass =
  'h-10 w-full rounded-md border border-border bg-card px-2 text-sm text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2';

export interface AccessibleGraphEditorProps {
  nodes: WorkflowNodeData[];
  edges: WorkflowEdgeData[];
  isEditable: boolean;
  onAddNode: (kind: NodeKind) => void;
  onRemoveNode: (nodeKey: string) => void;
  onAddEdge: (edge: WorkflowEdgeData) => void;
  onRemoveEdge: (index: number) => void;
}

/**
 * A plain form/list alternative to the canvas — every action here
 * (add/remove a node, connect two nodes, remove a connection) is a
 * standard control reachable and operable with the keyboard alone,
 * covering the parts of workflow configuration (drawing an edge by
 * dragging) that a pointer-only canvas interaction can't guarantee.
 */
export function AccessibleGraphEditor({
  nodes,
  edges,
  isEditable,
  onAddNode,
  onRemoveNode,
  onAddEdge,
  onRemoveEdge,
}: AccessibleGraphEditorProps) {
  return (
    <div className="space-y-6 p-4">
      <section aria-labelledby="nodes-heading">
        <h3 id="nodes-heading" className="mb-2 text-sm font-semibold text-text-primary">
          Nodes
        </h3>
        <ul className="mb-2 space-y-1">
          {nodes.map((node) => (
            <li
              key={node.node_key}
              className="flex items-center justify-between rounded-md border border-border bg-card px-2.5 py-1.5 text-sm"
            >
              <span>
                {node.node_key} — {NODE_CATALOG_BY_KIND[node.kind]?.label ?? node.kind}
              </span>
              {isEditable && (
                <IconButton aria-label={`Remove node ${node.node_key}`} onClick={() => onRemoveNode(node.node_key)}>
                  <Trash2 className="size-4" />
                </IconButton>
              )}
            </li>
          ))}
          {nodes.length === 0 && <li className="text-xs text-text-muted">No nodes yet.</li>}
        </ul>
        {isEditable && (
          <label className="block text-xs">
            <span className="mb-1 block font-medium text-text-primary">Add a node</span>
            <select
              className={nativeSelectClass}
              defaultValue=""
              onChange={(event) => {
                if (event.target.value) onAddNode(event.target.value as NodeKind);
                event.target.value = '';
              }}
            >
              <option value="" disabled>
                Choose a node type…
              </option>
              {NODE_CATALOG.map((entry) => (
                <option key={entry.kind} value={entry.kind}>
                  {entry.label}
                </option>
              ))}
            </select>
          </label>
        )}
      </section>

      <section aria-labelledby="edges-heading">
        <h3 id="edges-heading" className="mb-2 text-sm font-semibold text-text-primary">
          Connections
        </h3>
        <ul className="mb-2 space-y-1">
          {edges.map((edge, index) => (
            <li
              key={`${edge.source_node_key}-${edge.target_node_key}-${edge.branch}-${index}`}
              className="flex items-center justify-between rounded-md border border-border bg-card px-2.5 py-1.5 text-sm"
            >
              <span>
                {edge.source_node_key} {edge.branch && `(${edge.branch})`} → {edge.target_node_key}
              </span>
              {isEditable && (
                <IconButton aria-label={`Remove connection ${index + 1}`} onClick={() => onRemoveEdge(index)}>
                  <Trash2 className="size-4" />
                </IconButton>
              )}
            </li>
          ))}
          {edges.length === 0 && <li className="text-xs text-text-muted">No connections yet.</li>}
        </ul>
        {isEditable && nodes.length >= 2 && <EdgeForm nodes={nodes} onAddEdge={onAddEdge} />}
      </section>
    </div>
  );
}

function EdgeForm({
  nodes,
  onAddEdge,
}: {
  nodes: WorkflowNodeData[];
  onAddEdge: (edge: WorkflowEdgeData) => void;
}) {
  return (
    <form
      className="grid grid-cols-3 gap-2 text-xs"
      onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const source = String(form.get('source') ?? '');
        const target = String(form.get('target') ?? '');
        const branch = String(form.get('branch') ?? '') as WorkflowEdgeData['branch'];
        if (!source || !target) return;
        onAddEdge({ source_node_key: source, target_node_key: target, branch });
        event.currentTarget.reset();
      }}
    >
      <select name="source" defaultValue="" aria-label="From node" className={nativeSelectClass}>
        <option value="" disabled>
          From…
        </option>
        {nodes.map((n) => (
          <option key={n.node_key} value={n.node_key}>
            {n.node_key}
          </option>
        ))}
      </select>
      <select name="target" defaultValue="" aria-label="To node" className={nativeSelectClass}>
        <option value="" disabled>
          To…
        </option>
        {nodes.map((n) => (
          <option key={n.node_key} value={n.node_key}>
            {n.node_key}
          </option>
        ))}
      </select>
      <select
        name="branch"
        defaultValue=""
        aria-label="Branch (for condition nodes)"
        className={nativeSelectClass}
      >
        <option value="">No branch</option>
        <option value="true">true</option>
        <option value="false">false</option>
      </select>
      <Button type="submit" size="sm" variant="secondary" className="col-span-3">
        Add connection
      </Button>
    </form>
  );
}
