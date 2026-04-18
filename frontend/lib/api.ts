import type { FeedResponse, FeedItem, HealthResponse, SourceName, SortOption } from "./types";
import { DEFAULT_PAGE_SIZE } from "./constants";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FeedQueryParams {
  page?: number;
  per_page?: number;
  sources?: string;
  sort?: SortOption;
}

function buildQueryString(params: Record<string, string | number | boolean | undefined>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

async function apiRequest<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "Unknown error");
    throw new Error(
      `API request failed: ${response.status} ${response.statusText} - ${errorBody}`
    );
  }

  return response.json() as Promise<T>;
}

export async function getFeed(params?: FeedQueryParams): Promise<FeedResponse> {
  const query = buildQueryString({
    page: params?.page ?? 1,
    per_page: params?.per_page ?? DEFAULT_PAGE_SIZE,
    sources: params?.sources,
    sort: params?.sort,
  });
  return apiRequest<FeedResponse>(`/api/feed${query}`);
}

export async function getFeedItem(id: string): Promise<FeedItem> {
  return apiRequest<FeedItem>(`/api/feed/${encodeURIComponent(id)}`);
}

export async function getSources(): Promise<{ sources: { name: SourceName; label: string; enabled: boolean }[] }> {
  return apiRequest("/api/sources");
}

export async function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/api/health");
}
