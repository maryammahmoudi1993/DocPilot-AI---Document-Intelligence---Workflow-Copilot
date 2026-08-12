/** Mirrors backend/apps/assistant/models.py and serializers.py exactly. */

export type MessageRole = 'user' | 'assistant';

export interface AnswerCitation {
  id: string;
  document_id: string;
  filename: string;
  page_number: number;
  snippet: string;
  order: number;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  is_insufficient_evidence: boolean;
  citations: AnswerCitation[];
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  document_scope: string[];
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ConversationCreateRequest {
  document_scope?: string[];
}

export interface AskQuestionRequest {
  question: string;
}
