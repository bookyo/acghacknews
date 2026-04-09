import type { SourceName } from "./types";

export const SOURCE_CONFIG: Record<SourceName, { label: string; color: string }> = {
  reddit: { label: "Reddit", color: "text-orange-500" },
  anilist: { label: "AniList", color: "text-blue-500" },
  steam: { label: "Steam", color: "text-gray-400" },
  anime_news: { label: "Anime News", color: "text-purple-500" },
};

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 50;
