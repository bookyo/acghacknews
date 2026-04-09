# ACG Feed - Architecture Document

> Companion to `_index.md`. This document covers API integration patterns, data flow details, and component diagrams.
> Last updated: 2026-04-09 | Status: Pre-implementation

---

## 1. API Integration Reference

### 1.1 Reddit API

#### Overview

Reddit requires OAuth2 for API access. Since 2025, a "Responsible Builder Policy" requires pre-approval before new OAuth tokens are issued. Plan for a 1-5 day approval window.

**App Registration**: Create a "script" type application at https://www.reddit.com/prefs/apps. Use `http://localhost:8080` as the redirect URI for local testing.

**Authentication Flow (Client Credentials)**:

```
POST https://www.reddit.com/api/v1/access_token
  Content-Type: application/x-www-form-urlencoded
  Authorization: Basic base64(client_id:client_secret)
  Body: grant_type=client_credentials

Response:
  { "access_token": "...", "token_type": "bearer", "expires_in": 3600 }
```

Cache the token in memory. Refresh when expired (1-hour lifetime).

**Fetching Posts**:

```
GET https://oauth.reddit.com/r/{subreddit}/hot?limit=25
  Authorization: Bearer <access_token>
  User-Agent: acgfeed/1.0 (by /u/your_username)

Response: JSON with data.children[].data containing:
  - title, selftext, ups (upvotes), num_comments
  - permalink, url, created_utc
```

**Rate Limits**:
- OAuth-authenticated: 100 queries/minute per client ID (free tier)
- Without OAuth: 100 requests per 10 minutes
- Rate limiting is based on IP + User-Agent header
- Returns HTTP 429 when exceeded

**Subreddits**: r/anime, r/manga, r/Games

**Best Practices**:
- Always set a descriptive User-Agent header (required by Reddit policy)
- Implement exponential backoff on 429 responses
- Fetch only `hot` listings (top 25 per subreddit) to stay within rate limits
- 3 subreddits x 1 request each = 3 requests per 30-min cycle (well within limits)

**Fallback (if OAuth approval is denied)**: Use the `.json` endpoint
(`https://www.reddit.com/r/anime/hot.json`) which returns the same data
without OAuth but at lower rate limits. Set a custom User-Agent to avoid
aggressive throttling.

### 1.2 AniList GraphQL API

#### Overview

AniList provides a free GraphQL API for anime/manga data. No authentication required for public data.

**Endpoint**: `https://graphql.anilist.co`

**Rate Limit**: 90 requests per minute

**Query: Trending Anime**:

```graphql
query TrendingAnime {
  Page(page: 1, perPage: 25) {
    media(sort: TRENDING, type: ANIME, isAdult: false) {
      id
      title { romaji english native }
      description(asHtml: false)
      averageScore
      popularity
      trending
      episodes
      season
      seasonYear
      siteUrl
      coverImage { medium large }
    }
  }
}
```

**Query: Seasonal Anime (Current Season)**:

```graphql
query SeasonalAnime($season: MediaSeason, $seasonYear: Int) {
  Page(page: 1, perPage: 25) {
    media(
      sort: POPULARITY_DESC,
      type: ANIME,
      season: $season,
      seasonYear: $seasonYear,
      isAdult: false
    ) {
      id
      title { romaji english native }
      description(asHtml: false)
      averageScore
      popularity
      trending
      siteUrl
      coverImage { medium }
    }
  }
}
```

**Query: Trending Manga**:

```graphql
query TrendingManga {
  Page(page: 1, perPage: 15) {
    media(sort: TRENDING, type: MANGA, isAdult: false) {
      id
      title { romaji english native }
      description(asHtml: false)
      averageScore
      popularity
      trending
      siteUrl
      coverImage { medium }
    }
  }
}
```

**Request Format**:

```python
import httpx

response = await httpx.post(
    "https://graphql.anilist.co",
    json={"query": QUERY_STRING, "variables": {"season": "SPRING", "seasonYear": 2026}},
    headers={"Content-Type": "application/json", "Accept": "application/json"},
)
```

**Engagement Data Mapping**:
- `trending` (integer) -> primary engagement metric for heat score
- `popularity` (integer) -> secondary metric (number of users with entry on list)
- `averageScore` (0-100) -> quality indicator

### 1.3 Steam Store API

#### Overview

The Steam Store has undocumented but stable endpoints that do not require authentication. These power the Steam storefront itself.

**Key Endpoints**:

| Endpoint | Purpose |
|----------|---------|
| `https://store.steampowered.com/api/featured/` | Currently featured games and deals |
| `https://store.steampowered.com/api/featuredcategories/` | Categories: Coming Soon, Top Sellers, New Releases, Specials |
| `https://store.steampowered.com/api/appdetails?appids={ID}` | Detailed info for a specific game |

**Fetching Top Sellers / New Releases**:

```
GET https://store.steampowered.com/api/featuredcategories/?cc=us&l=english
```

Response contains arrays:
- `coming_soon.items[]` -- upcoming games
- `top_sellers.items[]` -- current best sellers
- `specials.items[]` -- games on sale

Each item includes: `id`, `name`, `small_capsule_image`, `header_image`,
`final_price`, `currency`.

**Fetching App Details**:

```
GET https://store.steampowered.com/api/appdetails?appids={APP_ID}&cc=us&l=english
```

Response includes: `name`, `short_description`, `header_image`,
`developers`, `publishers`, `price_overview`, `recommendations.total`,
`release_date`.

**Engagement Data Mapping**:
- `recommendations.total` (review count) -> primary engagement metric
- Price data -> useful for sale/special badges
- Release date -> useful for filtering upcoming vs. released

**Rate Limits**: No documented rate limits, but be respectful. One request
every 2-3 seconds is safe. We only need 2-3 requests per 30-min cycle.

**Important**: These are unofficial endpoints. They may change without notice.
Wrap all Steam API calls in try/except with graceful degradation.

### 1.4 Japanese Anime News RSS Feeds

#### Feed URLs

| Source | URL | Format |
|--------|-----|--------|
| Anime! Anime! | `https://animeanime.jp/rss/index.rdf` | RSS 1.0 (RDF) |
| MANTANWEB | `http://mantan-web.jp/index.rss` | RSS 2.0 |

#### Parsing Approach

Use Python `feedparser` library, which handles RSS 1.0, RSS 2.0, and Atom
transparently.

```python
import feedparser

feed = feedparser.parse("https://animeanime.jp/rss/index.rdf")
for entry in feed.entries:
    title = entry.title          # Japanese title
    link = entry.link            # URL to original article
    summary = entry.summary      # HTML summary, strip tags
    published = entry.published  # Publication date
```

**HTML Stripping**: RSS summaries often contain HTML. Use a library like
`html2text` or `bleach` to strip tags before translation.

**Engagement Data**: RSS feeds do not provide engagement metrics (views,
likes, comments). Heat score for RSS items is recency-only:
`1.0 * (1 / (1 + hours_since_fetch / 12))`.

**Character Encoding**: Japanese RSS feeds may use Shift-JIS or EUC-JP
encoding. `feedparser` handles most encoding issues automatically, but
verify with the actual feeds during development.

### 1.5 DeepSeek V3 Translation API

#### Overview

DeepSeek provides an OpenAI-compatible chat completions API. The current
production model is DeepSeek-V3.2, accessed via the `deepseek-chat` model
name (non-thinking mode).

**Endpoint**: Use OpenAI client with `base_url="https://api.deepseek.com"` (auto-appends `/v1/chat/completions`)

**Authentication**: Bearer token via API key.
```
Authorization: Bearer <DEEPSEEK_API_KEY>
```

**Rate Limits**: DeepSeek does not impose a fixed rate limit. They serve
requests as capacity allows. Throttling may occur under high server load.
Max output per request: 8,000 tokens.

**Pricing (as of 2026-04)**:

| Metric | Cost |
|--------|------|
| 1M input tokens (cache hit) | $0.028 |
| 1M input tokens (cache miss) | $0.28 |
| 1M output tokens | $0.42 |

**Translation Request Format**:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a professional translator specializing in ACG "
                "(Anime, Comic, Games) content. Translate the following "
                "text to simplified Chinese (zh-CN). Rules:\n"
                "1. Use established Chinese names for anime/manga titles "
                "(e.g., 'Jujutsu Kaisen' -> '咒术回战').\n"
                "2. Keep character names in their accepted Chinese forms.\n"
                "3. For terms without established translations, provide a "
                "transliteration and keep the original in parentheses.\n"
                "4. Maintain the tone and style of the original.\n"
                "5. Respond in JSON format: {\"title\": \"...\", \"body\": \"...\"}"
            ),
        },
        {
            "role": "user",
            "content": f"Title: {original_title}\nBody: {original_body}",
        },
    ],
    temperature=0.3,
    response_format={"type": "json_object"},
    max_tokens=2048,
)
```

**Cost Estimation for ~200 items/day**:

| Parameter | Value |
|-----------|-------|
| Items per day | ~200 (after deduplication) |
| Input tokens per item | ~200 (title + body + prompt overhead) |
| Output tokens per item | ~200 |
| Total input tokens/day | ~40,000 |
| Total output tokens/day | ~40,000 |
| Daily input cost (cache miss) | $0.011 |
| Daily output cost | $0.017 |
| **Total daily cost** | **~$0.03** |

Even with aggressive overestimates (3x), the daily cost stays under $0.10,
far below the $20 ceiling. Context caching further reduces cost by 90% for
repeated system prompts.

---

## 2. Data Flow Architecture

### 2.1 Complete Data Flow Diagram

```
+================================================================+
|                        CRON CYCLE                               |
|                  (every 30 minutes)                             |
+================================================================+
                              |
                              v
               +------------------------------+
               |     FETCH ORCHESTRATOR       |
               |  (asyncio.gather, parallel)  |
               +------------------------------+
                              |
       +----------+-----------+-----------+----------+
       |          |                       |          |
       v          v                       v          v
+-------------+ +-----------+      +-----------+ +----------+
|   REDDIT    | |  ANILIST  |      |   STEAM   | |  RSS JP  |
|   FETCHER   | |  FETCHER  |      |  FETCHER  | | FETCHER  |
|             | |           |      |           | |          |
| OAuth2 auth | | GraphQL   |      | Store API | | feed-    |
| GET hot/25  | | POST      |      | GET feat. | | parser   |
| x3 subredd. | | trending  |      | GET top   | | x2 feeds |
+-------------+ +-----------+      +-----------+ +----------+
       |                |                 |             |
       |  [timeout?]    | [timeout?]      | [timeout?]  | [timeout?]
       |  skip+log      | skip+log        | skip+log    | skip+log
       |                |                 |             |
       v                v                 v             v
+================================================================+
|              RAW ITEMS (in-memory list of dicts)               |
|   Each: {source, source_url, title, body, metadata}           |
+================================================================+
                              |
                              v
               +------------------------------+
               |    DEDUPLICATION FILTER      |
               |  SELECT source_url FROM      |
               |  feed_items WHERE ...        |
               |  Skip existing URLs          |
               +------------------------------+
                              |
                              v  (new items only)
               +------------------------------+
               |    TRANSLATION PIPELINE      |
               |                              |
               |  Group into batches of 10    |
               |  For each batch:             |
               |    POST deepseek/chat/comp.  |
               |    Parse JSON response       |
               |    On failure: retry x3      |
               |    On perm fail: mark text   |
               +------------------------------+
                              |
                              v
               +------------------------------+
               |   HEAT SCORE CALCULATOR      |
               |                              |
               |   score = (engagement^0.7)   |
               |     * 1/(1 + hours/24)       |
               |   RSS: recency-only          |
               +------------------------------+
                              |
                              v
               +------------------------------+
               |    DATABASE WRITE            |
               |    INSERT INTO feed_items    |
               |    UPDATE system_metadata    |
               +------------------------------+
                              |
                              v
               +------------------------------+
               |    CACHE INVALIDATION        |
               |    POST Vercel revalidation  |
               |    webhook (or set flag)     |
               +------------------------------+

===================== USER REQUEST FLOW ======================

  User Browser
       |
       v
  Vercel Edge CDN (cached HTML)
       |
       | (cache miss or stale > 5 min)
       v
  Next.js Server Component
       |
       | GET /api/feed?sort=hot&page=1&per_page=20
       v
  Railway FastAPI Backend
       |
       | SELECT * FROM feed_items
       |   WHERE source IN (...)
       |   ORDER BY heat_score DESC
       |   LIMIT 50 OFFSET 0
       v
  JSON Response (paginated)
       |
       v
  Server-rendered HTML cards
       |
       v
  User sees translated feed
```

### 2.2 Component Interaction Diagram

```
+---------------------------------------------------------------+
|                      RAILWAY BACKEND                           |
|                                                                |
|  +--------------------+    +------------------+                |
|  |   FastAPI App      |    |   APScheduler    |                |
|  |                    |    |                  |                |
|  |  /api/feed         |    |  fetch_all()     |                |
|  |  /api/sources      |    |  every 30 min    |                |
|  |  /api/health       |    +--------+---------+                |
|  |  /api/admin/*      |             |                          |
|  +--------+-----------+             v                          |
|           |              +--------------------+                |
|           |              | Source Fetchers    |                |
|           |              |                    |                |
|           |              | RedditFetcher      |                |
|           |              | AniListFetcher     |                |
|           |              | SteamFetcher       |                |
|           |              | RSSFetcher         |                |
|           |              +--------+-----------+                |
|           |                       |                            |
|           |              +--------v-----------+                |
|           |              | TranslationService  |                |
|           |              | (DeepSeek V3)       |                |
|           |              +--------+-----------+                |
|           |                       |                            |
|           |              +--------v-----------+                |
|           |              | ScoringService      |                |
|           |              +--------+-----------+                |
|           |                       |                            |
|  +--------v-----------+  +-------v------------+                |
|  |   FeedRepository   |  |   SQLite DB        |                |
|  |   (data access)    |--|   /data/acgfeed.db |                |
|  +--------------------+  +--------------------+                |
|                                                                |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
|                      VERCEL FRONTEND                           |
|                                                                |
|  +--------------------+    +------------------+                |
|  |   Next.js App      |    |  shadcn/ui       |                |
|  |   Router           |    |  Components      |                |
|  |                    |    |                  |                |
|  |  app/page.tsx      |    |  Card, Badge     |                |
|  |  app/layout.tsx    |    |  Checkbox, Toggle|                |
|  |                    |    |  Skeleton        |                |
|  +--------------------+    +------------------+                |
|           |                                                   |
|  +--------v-----------+                                       |
|  |   lib/api.ts        |  (fetch wrapper)                     |
|  |   lib/types.ts      |  (TypeScript interfaces)             |
|  |   lib/constants.ts  |  (source config, colors)             |
|  +--------------------+                                       |
|                                                                |
+---------------------------------------------------------------+

         External Services
         +------------------+
         | Reddit API       |
         | AniList API      |
         | Steam Store API  |
         | RSS Feeds (JP)   |
         | DeepSeek API     |
         +------------------+
```

### 2.3 Error Flow Diagram

```
Source API Call
       |
       +-- [Success] --> Raw item added to queue
       |
       +-- [Timeout > 10s] --> Log WARNING, skip source for this cycle
       |
       +-- [HTTP 429 Rate Limit] --> Backoff 30s, retry once
       |                           |
       |                           +-- [Success] --> add to queue
       |                           +-- [Fail] --> skip, log WARNING
       |
       +-- [HTTP 401/403] --> Log ERROR (auth issue), skip source
       |
       +-- [HTTP 5xx] --> Retry with backoff (1s, 3s, 5s)
       |                    |
       |                    +-- [Success] --> add to queue
       |                    +-- [Fail] --> skip, log WARNING
       |
       +-- [Network Error] --> Log WARNING, skip source

Translation Call
       |
       +-- [Success] --> Parse JSON, assign translations
       |
       +-- [Timeout > 30s] --> Retry x1
       |
       +-- [HTTP 429] --> Backoff 60s, retry once
       |
       +-- [Malformed JSON] --> Retry with stricter prompt x1
       |                        +-- [Fail] --> fall back to per-item translation
       |
       +-- [Permanent Fail] --> Store with original text
                               Mark with [TRANSLATION_PENDING] badge

All Sources Fail
       |
       +-- Log ERROR "All sources failed in cycle"
       +-- Keep existing data unchanged
       +-- Next cycle retries normally
```

---

## 3. Deployment Architecture

### 3.1 Infrastructure Diagram

```
                    +------------------+
                    |   User Browser   |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Vercel Edge CDN |
                    |  (Global PoPs)   |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Next.js App     |
                    |  (Serverless)    |
                    |                  |
                    |  - SSR pages     |
                    |  - ISR cache     |
                    |  - Static assets |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Railway Backend |
                    |  (Single Dyno)   |
                    |                  |
                    |  FastAPI + Uvicorn
                    |  APScheduler     |
                    |  +-------------+ |
                    |  | Persistent  | |
                    |  | Volume      | |
                    |  | /data/      | |
                    |  | acgfeed.db  | |
                    |  +-------------+ |
                    +--------+---------+
                             |
            +----------------+----------------+
            |                |                |
    +-------v------+ +------v-------+ +------v------+
    | Reddit API   | | AniList API  | | Steam API   |
    +--------------+ +--------------+ +------+------+
                                             |
                                    +--------v--------+
                                    | DeepSeek API    |
                                    | (Translation)   |
                                    +-----------------+
```

### 3.2 Railway Configuration

```yaml
# railway.toml or railway.json
[build]
  builder = "NIXPACKS"

[deploy]
  startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
  healthcheckPath = "/api/health"
  healthcheckTimeout = 30
  restartPolicyType = "ON_FAILURE"
  restartPolicyMaxRetries = 3

[[services]]
  name = "acgfeed-backend"

  [[services.volumes]]
    name = "acgfeed-data"
    mountPath = "/data"
```

### 3.3 Vercel Configuration

```json
{
  "framework": "nextjs",
  "buildCommand": "next build",
  "env": {
    "NEXT_PUBLIC_API_URL": "https://acgfeed-backend.up.railway.app"
  }
}
```

---

## 4. API Integration Implementation Patterns

### 4.1 Base Fetcher Pattern

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)

class BaseFetcher(ABC):
    """Base class for all source fetchers."""

    TIMEOUT = 10.0  # seconds
    MAX_RETRIES = 2

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """Fetch raw items from the source. Returns list of raw item dicts."""
        ...

    @abstractmethod
    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a raw item into the canonical internal format:
        {
            "source": str,
            "source_url": str,
            "original_title": str,
            "original_body": str,
            "source_metadata": dict,
            "engagement_metric": float,
        }
        """
        ...

    async def safe_fetch(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """Fetch with error handling. Returns empty list on failure."""
        try:
            raw_items = await self.fetch(client)
            return [self.normalize(item) for item in raw_items]
        except httpx.TimeoutException:
            logger.warning(f"{self.__class__.__name__}: Request timed out")
            return []
        except httpx.HTTPStatusError as e:
            logger.warning(f"{self.__class__.__name__}: HTTP {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: Unexpected error: {e}")
            return []
```

### 4.2 Translation Service Pattern

```python
class TranslationService:
    def __init__(self, api_key: str, batch_size: int = 10):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.batch_size = batch_size

    async def translate_batch(self, items: List[Dict]) -> List[Dict]:
        """Translate a batch of items. Returns items with translated fields."""
        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            translated = await self._call_api(batch)
            results.extend(translated)
        return results

    async def _call_api(self, batch: List[Dict]) -> List[Dict]:
        """Single API call for a batch. Includes retry logic."""
        for attempt in range(3):
            try:
                # Build prompt and call DeepSeek
                response = self.client.chat.completions.create(...)
                return self._parse_response(response, batch)
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Translation failed after 3 attempts: {e}")
                    return self._mark_failed(batch)
                await asyncio.sleep([1, 3, 5][attempt])
        return self._mark_failed(batch)
```

### 4.3 Heat Score Calculation

```python
import math
from datetime import datetime, timezone

def calculate_heat_score(
    engagement: float,
    fetched_at: datetime,
    source: str,
) -> float:
    """Calculate heat score for a feed item.

    Formula: score = (engagement ^ 0.7) * (1 / (1 + hours_since_fetch / 24))
    RSS feeds (no engagement data): score = 1.0 * (1 / (1 + hours_since_fetch / 12))
    """
    now = datetime.now(timezone.utc)
    hours_since = max(0, (now - fetched_at).total_seconds() / 3600)

    if source == "anime_news" or engagement <= 0:
        # Recency-only scoring for RSS items
        recency_factor = 1.0 / (1.0 + hours_since / 12.0)
        return round(recency_factor, 2)

    engagement_factor = math.pow(engagement, 0.7)
    recency_factor = 1.0 / (1.0 + hours_since / 24.0)
    return round(engagement_factor * recency_factor, 2)
```

### 4.4 Engagement Metrics by Source

| Source | Engagement Metric | Extraction |
|--------|------------------|------------|
| Reddit | `ups` (upvotes) | `item["data"]["ups"]` |
| AniList | `trending` score | `item["trending"]` (may be null; fall back to `popularity`) |
| Steam | `recommendations.total` (review count) | `appdetails["data"]["recommendations"]["total"]` |
| RSS | None (recency-only) | N/A |

---

## 5. Technology Decision Matrix

### 5.1 Why These External APIs

| Source | Why This API | Alternatives Considered |
|--------|-------------|------------------------|
| Reddit | Largest English ACG community discussions; structured data via JSON API; free tier sufficient | Twitter/X API (expensive, limited free tier), Discord (no public API for servers) |
| AniList | Best structured anime/manga database; free GraphQL API; includes trending/popularity scores | MyAnimeList API (restricted, requires approval), Kitsu (smaller dataset) |
| Steam | Dominant PC gaming platform; undocumented but stable Store API; no auth required | Epic Games Store (no public API), IGN/GameSpot (no structured API) |
| RSS (JP) | Direct access to Japanese anime news; stable RSS feeds; no auth required | Web scraping (fragile, harder to maintain) |
| DeepSeek V3 | Best Chinese language quality; 95% cheaper than GPT-4; ACG terminology understanding | Google Translate (poor ACG terminology), DeepL (no anime specialization), GPT-4 (expensive) |

---

## Appendix: Key URLs Quick Reference

| Resource | URL |
|----------|-----|
| Reddit App Registration | https://www.reddit.com/prefs/apps |
| Reddit OAuth Token | `https://www.reddit.com/api/v1/access_token` |
| Reddit API (OAuth) | `https://oauth.reddit.com/` |
| Reddit API (.json fallback) | `https://www.reddit.com/r/{sub}/{sort}.json` |
| AniList GraphQL | `https://graphql.anilist.co` |
| AniList API Docs | https://docs.anilist.co/ |
| Steam Featured | `https://store.steampowered.com/api/featured/` |
| Steam Featured Categories | `https://store.steampowered.com/api/featuredcategories/` |
| Steam App Details | `https://store.steampowered.com/api/appdetails?appids={ID}` |
| Anime! Anime! RSS | `https://animeanime.jp/rss/index.rdf` |
| MANTANWEB RSS | `http://mantan-web.jp/index.rss` |
| DeepSeek Chat Completions | `https://api.deepseek.com/chat/completions` |
| DeepSeek API Docs | https://api-docs.deepseek.com/ |
| DeepSeek Pricing | https://api-docs.deepseek.com/quick_start/pricing |
