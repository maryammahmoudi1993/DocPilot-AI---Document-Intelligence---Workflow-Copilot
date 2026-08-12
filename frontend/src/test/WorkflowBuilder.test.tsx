import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import {
  activateWorkflowHandler,
  buildVersion,
  buildWorkflow,
  buildWorkflowDetail,
  saveDraftHandler,
  testRunHandler,
  workflowDetailHandler,
  workflowListHandler,
  workflowRunsHandler,
} from '@/mocks/workflowHandlers';
import { WorkflowBuilderPage } from '@/pages/WorkflowBuilder';
import { renderWithProviders } from '@/test/testUtils';

function renderBuilder() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/workflows']}>
      <Routes>
        <Route path="/app/workflows" element={<WorkflowBuilderPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  server.use(...signedInHandlers, workflowRunsHandler([]));
});

describe('WorkflowBuilderPage', () => {
  it('shows an empty state when no workflow is selected', async () => {
    server.use(workflowListHandler([]));
    renderBuilder();

    expect(await screen.findByText('Select or create a workflow')).toBeInTheDocument();
  });

  it('lists workflows and loads the selected one onto the canvas', async () => {
    const detail = buildWorkflowDetail({
      draft_version: buildVersion({
        nodes: [
          { node_key: 't1', node_type: 'trigger', kind: 'document_uploaded', config: {}, position: { x: 0, y: 0 } },
        ],
        edges: [],
      }),
    });
    server.use(workflowListHandler([buildWorkflow()]), workflowDetailHandler(detail));
    const user = userEvent.setup();
    renderBuilder();

    await user.click(await screen.findByText('Invoice approval'));

    const canvas = await screen.findByRole('application', { name: 'Workflow canvas' });
    expect(await within(canvas).findByText('Document uploaded')).toBeInTheDocument();
  });

  it('adds a node from the palette by clicking it', async () => {
    const detail = buildWorkflowDetail({ draft_version: buildVersion() });
    server.use(workflowListHandler([buildWorkflow()]), workflowDetailHandler(detail));
    const user = userEvent.setup();
    renderBuilder();
    await user.click(await screen.findByText('Invoice approval'));

    await user.click(await screen.findByRole('button', { name: 'Document uploaded' }));

    // The canvas now renders the newly added trigger node.
    const canvas = screen.getByRole('application', { name: 'Workflow canvas' });
    expect(await within(canvas).findByText('Document uploaded')).toBeInTheDocument();
  });

  it('saves a draft and shows returned validation messages', async () => {
    const detail = buildWorkflowDetail({ draft_version: buildVersion() });
    server.use(
      workflowListHandler([buildWorkflow()]),
      workflowDetailHandler(detail),
      saveDraftHandler(buildVersion(), { validationErrors: ['A workflow must have exactly one trigger node.'] }),
    );
    const user = userEvent.setup();
    renderBuilder();
    await user.click(await screen.findByText('Invoice approval'));
    await user.click(await screen.findByRole('button', { name: 'Document uploaded' }));

    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(await screen.findByText('A workflow must have exactly one trigger node.')).toBeInTheDocument();
  });

  it('shows a stable error when activating an invalid graph', async () => {
    const detail = buildWorkflowDetail({ draft_version: buildVersion() });
    server.use(
      workflowListHandler([buildWorkflow()]),
      workflowDetailHandler(detail),
      saveDraftHandler(buildVersion()),
      activateWorkflowHandler({ error: 'This workflow graph is not valid.' }),
    );
    const user = userEvent.setup();
    renderBuilder();
    await user.click(await screen.findByText('Invoice approval'));

    await user.click(screen.getByRole('button', { name: /activate/i }));

    expect(await screen.findByText('This workflow graph is not valid.')).toBeInTheDocument();
  });

  it('runs a test run and shows it in the execution log', async () => {
    const detail = buildWorkflowDetail({ draft_version: buildVersion() });
    server.use(
      workflowListHandler([buildWorkflow()]),
      workflowDetailHandler(detail),
      saveDraftHandler(buildVersion()),
      testRunHandler({
        id: 'run-1',
        status: 'completed',
        trigger_context: {},
        is_test_run: true,
        error_code: '',
        step_runs: [],
        started_at: null,
        completed_at: null,
        created_at: '2026-08-12T00:00:00Z',
      }),
    );
    server.use(
      workflowRunsHandler([
        {
          id: 'run-1',
          status: 'completed',
          trigger_context: {},
          is_test_run: true,
          error_code: '',
          step_runs: [],
          started_at: null,
          completed_at: null,
          created_at: '2026-08-12T00:00:00Z',
        },
      ]),
    );
    const user = userEvent.setup();
    renderBuilder();
    await user.click(await screen.findByText('Invoice approval'));

    await user.click(screen.getByRole('button', { name: /test run/i }));

    await waitFor(() => expect(screen.getByText(/test run — completed/i)).toBeInTheDocument());
  });

  it('switches to the keyboard-friendly list view and adds a node without a pointer', async () => {
    const detail = buildWorkflowDetail({ draft_version: buildVersion() });
    server.use(workflowListHandler([buildWorkflow()]), workflowDetailHandler(detail));
    const user = userEvent.setup();
    renderBuilder();
    await user.click(await screen.findByText('Invoice approval'));

    await user.click(screen.getByRole('tab', { name: /list view/i }));
    await user.selectOptions(screen.getByLabelText('Add a node'), 'document_uploaded');

    expect(await screen.findByText(/node-1 — document uploaded/i)).toBeInTheDocument();
  });
});
