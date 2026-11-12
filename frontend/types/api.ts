// Mirrors the FastAPI response models in backend/app. Keep in sync.

export interface HealthResponse {
  status: "ok";
  app: string;
  version: string;
  environment: string;
  agent_provider: string;
}

export const CATEGORIES = ["community", "home", "blog", "faq", "landing"] as const;
export type Category = (typeof CATEGORIES)[number];

export const CONTENT_STATUSES = ["published", "draft", "archived"] as const;
export type ContentStatus = (typeof CONTENT_STATUSES)[number];

export const CONTENT_SORTS = ["updated_desc", "updated_asc", "title_asc"] as const;
export type ContentSort = (typeof CONTENT_SORTS)[number];

export interface ContentSummary {
  id: string;
  title: string;
  slug: string;
  category: Category;
  status: ContentStatus;
  updated_at: string;
  tags: string[];
  excerpt: string;
}

export interface ContentEntry {
  id: string;
  title: string;
  slug: string;
  content: string;
  category: Category;
  status: ContentStatus;
  created_at: string;
  updated_at: string;
  meta_title: string | null;
  meta_description: string | null;
  canonical_url: string | null;
  tags: string[];
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ContentQuery {
  q?: string;
  category?: Category;
  status?: ContentStatus;
  tag?: string;
  sort?: ContentSort;
  limit?: number;
  offset?: number;
}

export const PROPOSAL_STATUSES = ["pending", "approved", "rejected"] as const;
export type ProposalStatus = (typeof PROPOSAL_STATUSES)[number];
export type EditableField = "title" | "content" | "meta_title" | "meta_description";

export interface Proposal {
  id: string;
  content_id: string;
  field_name: EditableField;
  original_value: string | null;
  proposed_value: string;
  rationale: string;
  evidence_excerpt: string;
  status: ProposalStatus;
  created_at: string;
  reviewed_at: string | null;
  review_note: string | null;
}

export const EVENT_TYPES = [
  "tool_call",
  "proposal_created",
  "proposal_approved",
  "proposal_rejected",
  "error",
] as const;
export type EventType = (typeof EVENT_TYPES)[number];

export interface ActivityEvent {
  id: string;
  event_type: EventType;
  actor: "assistant" | "editor" | "system";
  tool_name: string | null;
  details: Record<string, unknown>;
  status: string;
  created_at: string;
}
