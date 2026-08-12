import { useEffect, useMemo, useState } from 'react';
import { Play, Power, PowerOff, Save, Workflow as WorkflowIcon } from 'lucide-react';
import { useSession } from '@/features/auth/hooks';
import { MANAGER_ROLES } from '@/features/auth/types';
import {
  useActivateWorkflow,
  useCreateWorkflow,
  useDeactivateWorkflow,
  useSaveDraft,
  useTestRunWorkflow,
  useWorkflow,
  useWorkflowRuns,
  useWorkflows,
} from '@/features/workflows/hooks';
import type { NodeKind, WorkflowEdgeData, WorkflowNodeData } from '@/features/workflows/types';
import { ApiError } from '@/lib/apiClient';
import { Button } from '@/components/ui/Button';
import { FullPageSpinner } from '@/components/ui/FullPageSpinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { NODE_CATALOG_BY_KIND } from '@/components/workflows/nodeCatalog';
import { NodePalette } from '@/components/workflows/NodePalette';
import { WorkflowCanvas } from '@/components/workflows/WorkflowCanvas';
import { NodeSettingsPanel } from '@/components/workflows/NodeSettingsPanel';
import { ValidationMessages } from '@/components/workflows/ValidationMessages';
import { ExecutionLog } from '@/components/workflows/ExecutionLog';
import { AccessibleGraphEditor } from '@/components/workflows/AccessibleGraphEditor';

export function WorkflowBuilderPage() {
  const { data: session } = useSession();
  const workspaceId = session?.active_workspace_id ?? undefined;
  const role = session?.workspaces.find((w) => w.id === workspaceId)?.role;
  const canEdit = Boolean(role && MANAGER_ROLES.includes(role));

  const workflowsQuery = useWorkflows(workspaceId);
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);
  const workflowQuery = useWorkflow(workspaceId, activeWorkflowId ?? undefined);
  const runsQuery = useWorkflowRuns(workspaceId, activeWorkflowId ?? undefined);

  const createWorkflow = useCreateWorkflow(workspaceId);
  const saveDraft = useSaveDraft(workspaceId, activeWorkflowId ?? undefined);
  const activateWorkflow = useActivateWorkflow(workspaceId, activeWorkflowId ?? undefined);
  const deactivateWorkflow = useDeactivateWorkflow(workspaceId, activeWorkflowId ?? undefined);
  const testRun = useTestRunWorkflow(workspaceId, activeWorkflowId ?? undefined);

  const [nodes, setNodes] = useState<WorkflowNodeData[]>([]);
  const [edges, setEdges] = useState<WorkflowEdgeData[]>([]);
  const [selectedNodeKey, setSelectedNodeKey] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isDirty, setIsDirty] = useState(false);
  const [activateError, setActivateError] = useState<string | null>(null);
  const [showLog, setShowLog] = useState(false);

  // Loads the working graph whenever a *different* workflow finishes
  // loading — the draft if one exists (edits always land there),
  // otherwise the active version as a read/edit starting point (saving
  // creates a new draft on the backend automatically). Adjusted during
  // render (React's documented pattern for resetting state when a prop/
  // query key changes) rather than in an effect keyed on the query
  // result object, specifically so a background refetch of the *same*
  // workflow (e.g. on window focus) can never silently discard
  // in-progress local edits — only an actual workflow-id change resets.
  const [loadedWorkflowId, setLoadedWorkflowId] = useState<string | null>(null);
  if (workflowQuery.data && workflowQuery.data.id !== loadedWorkflowId) {
    const version = workflowQuery.data.draft_version ?? workflowQuery.data.active_version;
    setLoadedWorkflowId(workflowQuery.data.id);
    setNodes(version?.nodes ?? []);
    setEdges(version?.edges ?? []);
    setValidationErrors(version?.validation_errors ?? []);
    setIsDirty(false);
    setSelectedNodeKey(null);
  }

  // Unsaved-change protection (tab close/refresh) — matches the pattern
  // already used on the extraction review page.
  useEffect(() => {
    function handler(event: BeforeUnloadEvent) {
      if (isDirty) event.preventDefault();
    }
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.node_key === selectedNodeKey) ?? null,
    [nodes, selectedNodeKey],
  );
  const errorNodeKeys = useMemo(() => new Set<string>(), []); // node-level error mapping not modeled server-side yet

  function handleSelectWorkflow(id: string) {
    if (isDirty && !window.confirm('You have unsaved changes. Switch workflows anyway?')) return;
    setActiveWorkflowId(id);
  }

  async function handleNewWorkflow() {
    const name = window.prompt('Workflow name?');
    if (!name) return;
    const created = await createWorkflow.mutateAsync(name);
    setActiveWorkflowId(created.id);
  }

  function handleAddNode(kind: NodeKind, position: { x: number; y: number } = { x: 100, y: 100 }) {
    const entry = NODE_CATALOG_BY_KIND[kind];
    if (!entry) return;
    setNodes((prev) => {
      const maxIndex = prev.reduce((max, n) => {
        const match = /-(\d+)$/.exec(n.node_key);
        return match ? Math.max(max, Number(match[1])) : max;
      }, 0);
      const nodeKey = `node-${maxIndex + 1}`;
      return [...prev, { node_key: nodeKey, node_type: entry.nodeType, kind, config: {}, position }];
    });
    setIsDirty(true);
  }

  function handleRemoveNode(nodeKey: string) {
    setNodes((prev) => prev.filter((n) => n.node_key !== nodeKey));
    setEdges((prev) => prev.filter((e) => e.source_node_key !== nodeKey && e.target_node_key !== nodeKey));
    if (selectedNodeKey === nodeKey) setSelectedNodeKey(null);
    setIsDirty(true);
  }

  function handleMoveNode(nodeKey: string, position: { x: number; y: number }) {
    setNodes((prev) => prev.map((n) => (n.node_key === nodeKey ? { ...n, position } : n)));
    setIsDirty(true);
  }

  function handleAddEdge(edge: WorkflowEdgeData) {
    setEdges((prev) => [...prev, edge]);
    setIsDirty(true);
  }

  function handleRemoveEdge(index: number) {
    setEdges((prev) => prev.filter((_, i) => i !== index));
    setIsDirty(true);
  }

  function handleNodeConfigChange(config: Record<string, unknown>) {
    if (!selectedNodeKey) return;
    setNodes((prev) => prev.map((n) => (n.node_key === selectedNodeKey ? { ...n, config } : n)));
    setIsDirty(true);
  }

  async function handleSave() {
    const result = await saveDraft.mutateAsync({ nodes, edges });
    setValidationErrors(result.validation_errors ?? []);
    setIsDirty(false);
  }

  async function handleActivate() {
    setActivateError(null);
    if (isDirty) await handleSave();
    try {
      await activateWorkflow.mutateAsync();
    } catch (error) {
      if (error instanceof ApiError) setActivateError(error.message);
    }
  }

  async function handleTestRun() {
    if (isDirty) await handleSave();
    await testRun.mutateAsync({});
    setShowLog(true);
  }

  if (!workspaceId || workflowsQuery.isLoading) {
    return <FullPageSpinner />;
  }

  const workflow = workflowQuery.data;

  return (
    <div className="flex h-full">
      <div className="w-56 shrink-0 border-r border-border bg-sidebar p-3">
        {canEdit && (
          <Button type="button" variant="secondary" size="sm" className="mb-3 w-full" onClick={handleNewWorkflow}>
            New workflow
          </Button>
        )}
        <ul className="space-y-1">
          {(workflowsQuery.data ?? []).map((w) => (
            <li key={w.id}>
              <button
                type="button"
                onClick={() => handleSelectWorkflow(w.id)}
                className={`w-full rounded-md px-2.5 py-2 text-left text-sm transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                  activeWorkflowId === w.id
                    ? 'bg-primary-soft text-primary'
                    : 'text-text-secondary hover:bg-lavender hover:text-text-primary'
                }`}
              >
                {w.name}
                {w.is_active && <span className="ml-1.5 text-xs text-status-approved">● active</span>}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {!activeWorkflowId || !workflow ? (
        <div className="flex flex-1 items-center justify-center">
          <EmptyState
            icon={WorkflowIcon}
            title="Select or create a workflow"
            description="Build an approval or automation workflow with triggers, conditions, and actions."
          />
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex items-center justify-between border-b border-border bg-card px-4 py-2.5">
            <h1 className="text-sm font-semibold text-text-primary">{workflow.name}</h1>
            <div className="flex items-center gap-2">
              <Button type="button" variant="secondary" size="sm" onClick={handleTestRun} isLoading={testRun.isPending}>
                <Play className="mr-1 size-4" /> Test run
              </Button>
              {canEdit && (
                <>
                  <Button type="button" variant="secondary" size="sm" onClick={handleSave} isLoading={saveDraft.isPending}>
                    <Save className="mr-1 size-4" /> Save
                  </Button>
                  {workflow.is_active ? (
                    <Button type="button" variant="destructive" size="sm" onClick={() => deactivateWorkflow.mutate()}>
                      <PowerOff className="mr-1 size-4" /> Deactivate
                    </Button>
                  ) : (
                    <Button type="button" variant="primary" size="sm" onClick={handleActivate} isLoading={activateWorkflow.isPending}>
                      <Power className="mr-1 size-4" /> Activate
                    </Button>
                  )}
                </>
              )}
              <Button type="button" variant="ghost" size="sm" onClick={() => setShowLog((v) => !v)}>
                Execution log
              </Button>
            </div>
          </div>

          {activateError && <ValidationMessages errors={[activateError]} />}
          <ValidationMessages errors={validationErrors} />

          <Tabs defaultValue="canvas" className="flex min-h-0 flex-1 flex-col">
            <TabsList className="mx-4 mt-2 w-fit">
              <TabsTrigger value="canvas">Canvas</TabsTrigger>
              <TabsTrigger value="list">List view (keyboard-friendly)</TabsTrigger>
            </TabsList>

            <TabsContent value="canvas" className="min-h-0 flex-1">
              <div className="flex h-full">
                {canEdit && <NodePalette onAdd={(kind) => handleAddNode(kind)} />}
                <WorkflowCanvas
                  nodes={nodes}
                  edges={edges}
                  selectedNodeKey={selectedNodeKey}
                  errorNodeKeys={errorNodeKeys}
                  isEditable={canEdit}
                  onSelectNode={setSelectedNodeKey}
                  onMoveNode={handleMoveNode}
                  onAddNode={handleAddNode}
                  onAddEdge={handleAddEdge}
                />
                {selectedNode && (
                  <NodeSettingsPanel
                    node={selectedNode}
                    isEditable={canEdit}
                    onChange={handleNodeConfigChange}
                    onDelete={() => handleRemoveNode(selectedNode.node_key)}
                    onClose={() => setSelectedNodeKey(null)}
                  />
                )}
              </div>
            </TabsContent>

            <TabsContent value="list" className="min-h-0 flex-1 overflow-y-auto">
              <AccessibleGraphEditor
                nodes={nodes}
                edges={edges}
                isEditable={canEdit}
                onAddNode={(kind) => handleAddNode(kind)}
                onRemoveNode={handleRemoveNode}
                onAddEdge={handleAddEdge}
                onRemoveEdge={handleRemoveEdge}
              />
            </TabsContent>
          </Tabs>

          {showLog && (
            <div className="max-h-64 overflow-y-auto border-t border-border">
              <ExecutionLog runs={runsQuery.data ?? []} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
