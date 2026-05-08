// ──────────────────────────────────────────────────────────────
// Gmail connector request / response interfaces
// ──────────────────────────────────────────────────────────────

/** Parameters for sending an email through Gmail. */
export interface SendEmailParams {
  to: string;
  subject: string;
  body: string;
  /** Optional CC recipients */
  cc?: string[];
  /** Optional BCC recipients */
  bcc?: string[];
  /** MIME content type — defaults to 'text/plain' */
  contentType?: 'text/plain' | 'text/html';
}

/** Response after sending an email. */
export interface SendEmailResult {
  messageId: string;
  threadId: string;
  labelIds: string[];
}

/** Parameters for listing emails. */
export interface ListEmailsParams {
  /** Gmail search query (same syntax as the Gmail search box). */
  query?: string;
  /** Maximum number of results (default 10, max 100). */
  maxResults?: number;
  /** Pagination token returned by a previous list call. */
  pageToken?: string;
}

/** A slim email summary returned by the list endpoint. */
export interface EmailSummary {
  id: string;
  threadId: string;
  snippet: string;
  from?: string;
  to?: string;
  subject?: string;
  date?: string;
  labelIds: string[];
}

/** Paginated list of email summaries. */
export interface ListEmailsResult {
  messages: EmailSummary[];
  nextPageToken?: string;
  resultSizeEstimate: number;
}

/** Full email detail returned by getEmail. */
export interface EmailDetail {
  id: string;
  threadId: string;
  snippet: string;
  labelIds: string[];
  from?: string;
  to?: string;
  subject?: string;
  date?: string;
  body?: string;
  contentType?: string;
}
