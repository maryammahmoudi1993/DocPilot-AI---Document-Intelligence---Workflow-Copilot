export type DocumentStatus = 'uploaded' | 'archived';

export interface DocumentOwner {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

/** Matches `DocumentSerializer` (backend/apps/documents/serializers.py) —
 * the shape returned by list, archive, and bulk-archive responses. */
export interface DocumentSummary {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  checksum_sha256: string;
  status: DocumentStatus;
  uploaded_by: DocumentOwner | null;
  created_at: string;
  archived_at: string | null;
}

/** `DocumentDetailSerializer` — adds a freshly-generated, short-lived
 * signed URL. Never persist `download_url` beyond the response that
 * carried it (see DocumentsPage's download handler). */
export interface DocumentDetail extends DocumentSummary {
  download_url: string;
}

export interface DocumentListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: DocumentSummary[];
}

export type DocumentOrdering = 'created_at' | '-created_at' | 'size_bytes' | '-size_bytes' | 'filename' | '-filename';

export interface DocumentListParams {
  status?: DocumentStatus;
  content_type?: string;
  search?: string;
  ordering?: DocumentOrdering;
  page?: number;
  page_size?: number;
}
