import { useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Connection,
  type Edge,
  type Node,
  type NodeMouseHandler,
  type ReactFlowInstance,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { GraphNode, type GraphNodeData } from './GraphNode';
import type { NodeKind, WorkflowEdgeData, WorkflowNodeData } from '@/features/workflows/types';

export interface WorkflowCanvasProps {
  nodes: WorkflowNodeData[];
  edges: WorkflowEdgeData[];
  selectedNodeKey: string | null;
  errorNodeKeys: Set<string>;
  isEditable: boolean;
  onSelectNode: (nodeKey: string | null) => void;
  onMoveNode: (nodeKey: string, position: { x: number; y: number }) => void;
  onAddNode: (kind: NodeKind, position: { x: number; y: number }) => void;
  onAddEdge: (edge: WorkflowEdgeData) => void;
}

const nodeTypes = { graphNode: GraphNode };

export function WorkflowCanvas({
  nodes,
  edges,
  selectedNodeKey,
  errorNodeKeys,
  isEditable,
  onSelectNode,
  onMoveNode,
  onAddNode,
  onAddEdge,
}: WorkflowCanvasProps) {
  const instanceRef = useRef<ReactFlowInstance | null>(null);

  const flowNodes: Node[] = useMemo(
    () =>
      nodes.map((n) => ({
        id: n.node_key,
        type: 'graphNode',
        position: n.position?.x !== undefined ? n.position : { x: 0, y: 0 },
        selected: n.node_key === selectedNodeKey,
        draggable: isEditable,
        data: {
          kind: n.kind,
          node_type: n.node_type,
          nodeKey: n.node_key,
          hasError: errorNodeKeys.has(n.node_key),
        } satisfies GraphNodeData,
      })),
    [nodes, selectedNodeKey, errorNodeKeys, isEditable],
  );

  const flowEdges: Edge[] = useMemo(
    () =>
      edges.map((e, index) => ({
        id: `${e.source_node_key}-${e.branch}-${e.target_node_key}-${index}`,
        source: e.source_node_key,
        target: e.target_node_key,
        sourceHandle: e.branch || undefined,
        label: e.branch || undefined,
        animated: false,
      })),
    [edges],
  );

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_, node) => onSelectNode(node.id),
    [onSelectNode],
  );

  const handleConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;
      onAddEdge({
        source_node_key: connection.source,
        target_node_key: connection.target,
        branch: (connection.sourceHandle as 'true' | 'false' | null) ?? '',
      });
    },
    [onAddEdge],
  );

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const kind = event.dataTransfer.getData('application/docpilot-node-kind') as NodeKind;
      if (!kind || !instanceRef.current) return;
      const position = instanceRef.current.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });
      onAddNode(kind, position);
    },
    [onAddNode],
  );

  return (
    <div
      className="h-full flex-1"
      onDrop={handleDrop}
      onDragOver={(event) => event.preventDefault()}
      role="application"
      aria-label="Workflow canvas"
    >
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        onInit={(instance) => {
          instanceRef.current = instance;
        }}
        onNodeClick={handleNodeClick}
        onPaneClick={() => onSelectNode(null)}
        onNodeDragStop={(_, node) => onMoveNode(node.id, node.position)}
        onConnect={handleConnect}
        nodesDraggable={isEditable}
        nodesConnectable={isEditable}
        elementsSelectable
        fitView
      >
        <Background />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  );
}
