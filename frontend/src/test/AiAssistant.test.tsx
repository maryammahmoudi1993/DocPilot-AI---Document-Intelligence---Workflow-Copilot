import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { server } from '@/mocks/server';
import { signedInHandlers } from '@/mocks/handlers';
import { documentHandlers } from '@/mocks/documentHandlers';
import {
  askQuestionHandler,
  buildAssistantMessage,
  buildConversation,
  conversationDetailHandler,
  conversationListHandler,
  createConversationHandler,
} from '@/mocks/assistantHandlers';
import { AiAssistantPage } from '@/pages/AiAssistant';
import { renderWithProviders } from '@/test/testUtils';

vi.mock('pdfjs-dist', () => ({
  GlobalWorkerOptions: {},
  getDocument: () => ({
    promise: Promise.resolve({
      numPages: 1,
      getPage: () =>
        Promise.resolve({
          getViewport: () => ({ width: 100, height: 100 }),
          render: () => ({ promise: Promise.resolve() }),
        }),
    }),
  }),
}));

function renderAssistant() {
  return renderWithProviders(
    <MemoryRouter initialEntries={['/app/assistant']}>
      <Routes>
        <Route path="/app/assistant" element={<AiAssistantPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  server.use(...signedInHandlers, ...documentHandlers);
});

describe('AiAssistantPage', () => {
  it('shows conversation history and suggested questions when empty', async () => {
    server.use(conversationListHandler([{ id: 'conv-1', title: 'Prior chat', document_scope: [], created_at: '', updated_at: '' }]));
    renderAssistant();

    expect(await screen.findByText('Prior chat')).toBeInTheDocument();
    expect(screen.getByText('Ask a grounded question')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /summarize the key terms/i })).toBeInTheDocument();
  });

  it('loads an existing conversation and shows its messages with citations', async () => {
    const conversation = buildConversation({
      id: 'conv-1',
      messages: [
        { id: 'm1', role: 'user', content: 'What is the total?', is_insufficient_evidence: false, citations: [], created_at: '' },
        buildAssistantMessage(),
      ],
    });
    server.use(
      conversationListHandler([{ id: 'conv-1', title: '', document_scope: [], created_at: '', updated_at: '' }]),
      conversationDetailHandler(conversation),
    );
    renderAssistant();
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: /untitled conversation/i }));

    expect(await screen.findByText('What is the total?')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /acme-invoice-0142\.pdf · p\.1/i })).toBeInTheDocument();
  });

  it('asks a question via a suggested prompt, stages "Thinking…", and renders the grounded answer', async () => {
    server.use(
      conversationListHandler([]),
      createConversationHandler(buildConversation({ id: 'conv-new' })),
      askQuestionHandler(buildAssistantMessage(), { delayMs: 50 }),
      // Fetched again after asking (the mutation invalidates the
      // conversation-detail query) — without this mock, the answer
      // would never actually render even though the ask itself
      // succeeds, which is exactly the gap this test caught.
      conversationDetailHandler(
        buildConversation({
          id: 'conv-new',
          messages: [
            {
              id: 'm-user',
              role: 'user',
              content: 'What is the total on the most recent invoice?',
              is_insufficient_evidence: false,
              citations: [],
              created_at: '',
            },
            buildAssistantMessage(),
          ],
        }),
      ),
    );
    renderAssistant();
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: /what is the total on the most recent invoice/i }));

    expect(await screen.findByRole('status')).toHaveTextContent('Thinking…');
    await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument());
    expect(await screen.findByRole('button', { name: /acme-invoice-0142\.pdf · p\.1/i })).toBeInTheDocument();
  });

  it('lets the user cancel an in-flight question', async () => {
    server.use(
      conversationListHandler([]),
      createConversationHandler(buildConversation({ id: 'conv-new' })),
      askQuestionHandler(buildAssistantMessage(), { delayMs: 5000 }),
    );
    renderAssistant();
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: /what is the total on the most recent invoice/i }));
    await screen.findByRole('status');

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument());
  });

  it('opens the source panel at the cited document and page when a citation is clicked', async () => {
    const conversation = buildConversation({ id: 'conv-1', messages: [buildAssistantMessage()] });
    server.use(
      conversationListHandler([{ id: 'conv-1', title: '', document_scope: [], created_at: '', updated_at: '' }]),
      conversationDetailHandler(conversation),
    );
    renderAssistant();
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: /untitled conversation/i }));

    await user.click(await screen.findByRole('button', { name: /acme-invoice-0142\.pdf · p\.1/i }));

    expect(await screen.findByRole('heading', { name: 'Source' })).toBeInTheDocument();
  });

  it('shows an insufficient-evidence answer distinctly', async () => {
    const conversation = buildConversation({
      id: 'conv-1',
      messages: [
        buildAssistantMessage({
          id: 'm2',
          content: "I don't have enough grounded information in the indexed documents to answer that.",
          is_insufficient_evidence: true,
          citations: [],
        }),
      ],
    });
    server.use(
      conversationListHandler([{ id: 'conv-1', title: '', document_scope: [], created_at: '', updated_at: '' }]),
      conversationDetailHandler(conversation),
    );
    renderAssistant();
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: /untitled conversation/i }));

    expect(await screen.findByText('Insufficient evidence')).toBeInTheDocument();
  });

  it('shows a provider-error state with a retry action', async () => {
    server.use(
      conversationListHandler([]),
      createConversationHandler(buildConversation({ id: 'conv-new' })),
      askQuestionHandler(buildAssistantMessage(), { providerError: true }),
    );
    renderAssistant();
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: /what is the total on the most recent invoice/i }));

    expect(await screen.findByText('The assistant is temporarily unavailable')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('lets the user narrow a new conversation to specific documents', async () => {
    server.use(conversationListHandler([]));
    renderAssistant();

    expect(await screen.findByText('acme-invoice-0142.pdf')).toBeInTheDocument();
    const [checkbox] = screen.getAllByRole('checkbox');
    expect(screen.getByText(/\(all documents\)/)).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(checkbox!);

    expect(screen.getByText(/\(1 selected\)/)).toBeInTheDocument();
  });
});
