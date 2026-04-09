export type SourceName = "reddit" | "anilist" | "steam" | "anime_news";
export type SortOption = "hot" | "new";

export interface FeedItem {
  id: string;
  source: SourceName;
  source_url: string;
  translated_title: string;
  translated_body: string;
  heat_score: number;
  source_metadata: Record<string, unknown>;
  fetched_at: string;
  translated_at: string | null;
  language: string;
}

export interface FeedResponse {
  items: FeedItem[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
}

export interface SourceConfig {
  name: SourceName;
  label: string;
  enabled: boolean;
}

export interface HealthResponse {
  status: string;
  last_fetch_at: string | null;
  total_items: number;
  db_size_mb: number;
  last_fetch_status?: string;
}
