import { Handle, Position, type NodeProps } from '@xyflow/react';
import { NODE_CATALOG_BY_KIND } from './nodeCatalog';
import { cn } from '@/lib/utils';

export interface GraphNodeData extends Record<string, unknown> {
  kind: string;
  node_type: 'trigger' | 'condition' | 'action';
  nodeKey: string;
  hasError?: boolean;
}

const COLOR_BY_TYPE: Record<string, string> = {
  trigger: 'border-status-approved bg-status-approved-bg text-status-approved',
  condition: 'border-status-review bg-status-review-bg text-status-review',
  action: 'border-primary bg-primary-soft text-primary',
};

/** One React Flow node — trigger/action have a single output handle;
 * condition nodes have two, labeled true/false, so an edge's branch is
 * visually unambiguous while connecting it. */
export function GraphNode({ data, selected }: NodeProps & { data: GraphNodeData }) {
  const entry = NODE_CATALOG_BY_KIND[data.kind];
  const Icon = entry?.icon;

  return (
    <div
      className={cn(
        'min-w-40 rounded-lg border-2 bg-card px-3 py-2 shadow-sm transition-colors duration-fast',
        COLOR_BY_TYPE[data.node_type],
        selected && 'ring-2 ring-primary ring-offset-2',
        data.hasError && 'border-status-failed',
      )}
    >
      {data.node_type !== 'trigger' && (
        <Handle type="target" position={Position.Left} className="!bg-text-muted" />
      )}

      <div className="flex items-center gap-1.5 text-xs font-semibold">
        {Icon && <Icon className="size-3.5" aria-hidden="true" />}
        {entry?.label ?? data.kind}
      </div>
      <div className="mt-0.5 text-xs text-text-secondary">{data.nodeKey}</div>

      {data.node_type === 'condition' ? (
        <>
          <Handle
            type="source"
            position={Position.Right}
            id="true"
            style={{ top: '35%' }}
            className="!bg-status-approved"
          />
          <Handle
            type="source"
            position={Position.Right}
            id="false"
            style={{ top: '65%' }}
            className="!bg-status-failed"
          />
          <div className="pointer-events-none mt-1 flex justify-between text-[10px] text-text-muted">
            <span>true</span>
            <span>false</span>
          </div>
        </>
      ) : (
        <Handle type="source" position={Position.Right} className="!bg-text-muted" />
      )}
    </div>
  );
}
