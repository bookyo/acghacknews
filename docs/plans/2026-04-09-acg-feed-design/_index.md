# ACG Feed - Design Document

> AI-translated Anime, Manga & Game News Aggregator
> Last updated: 2026-04-09 | Status: Pre-implementation

---

## 1. Context

### Problem Statement

Chinese-speaking ACG (Anime, Comic, Games) enthusiasts face a language barrier when accessing the best English and Japanese community discussions and news. Content from Reddit (r/anime, r/manga, r/Games), AniList trending entries, Steam game updates, and Japanese anime news sites remains locked behind language that most casual Chinese readers cannot comfortably consume at speed.

Existing solutions require users to visit multiple sites, each in a different language, and manually translate content piecemeal. No single destination provides a curated, translated, heat-ranked feed of ACG content from these major sources.

### Target User

**Primary persona**: Chinese-speaking ACG fan, 18-30 years old, who browses anime/game news daily but struggles with English and Japanese. They want a single place to skim what is trending across the global ACG community, presented in natural-sounding Chinese.

**Not the user for MVP**: Content creators, community moderators, non-Chinese speakers, people looking for social interaction.

### Narrowest Wedge

A single-column, translation-first feed aggregator that:
1. Pulls from exactly four high-signal sources (Reddit, AniList, Steam, Japanese RSS).
2. Translates every item to zh-CN using an LLM that understands ACG terminology.
3. Ranks by a transparent heat score combining source engagement with recency.

This is the thinnest possible slice that delivers the core value proposition: "see what the global ACG community cares about, in Chinese." No accounts, no social features, no search -- just a feed.

### Success Metrics

| Timeframe | Metric | Target |
|-----------|--------|--------|
| Week 1 | Prototype shared | 10 target users |
| Week 2 | Day-7 retention | 3+ users return |
| Week 4 | DAU | 20+ DAU, organic sharing |
| Kill criterion | Day-7 retention | <2 users return (kill or pivot) |

### Constraints

- Solo founder/engineer with limited bandwidth.
- Pre-product, zero users, zero revenue.
- Must be mobile-friendly (responsive web).
- Translation API costs must stay under $20/day at projected MVP scale.
- No user accounts or authentication for MVP.

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F-01 | System fetches content from Reddit (r/anime, r/manga, r/Games) every 30 minutes | Must |
| F-02 | System fetches trending content from AniList every 30 minutes | Must |
| F-03 | System fetches new/popular games from Steam every 30 minutes | Must |
| F-04 | System fetches Japanese anime news via RSS feeds every 30 minutes | Must |
| F-05 | Every fetched item is translated to zh-CN (title + body excerpt) via DeepSeek V3 | Must |
| F-06 | Feed items are scored using the heat score algorithm and stored | Must |
| F-07 | Frontend displays a single-column card feed, sorted by heat (default) or recency | Must |
| F-08 | Users can filter feed by source (checkboxes for each source) | Must |
| F-09 | Each card shows: source badge, translated title, translated excerpt, heat score, timestamp | Must |
| F-10 | Each card has a collapsible "View original" link to the source URL | Must |
| F-11 | Top bar includes: logo, source filter checkboxes, hot/new sort toggle | Must |
| F-12 | Placeholder (disabled) buttons for future Social and Search tabs | Should |
| F-13 | Feed is responsive and mobile-friendly | Must |
| F-14 | Original body text is truncated to 500 characters before storage | Must |
| F-15 | Duplicate items from the same source_url are deduplicated | Must |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NF-01 | Page load time (first contentful paint) | < 2 seconds |
| NF-02 | API response time (feed endpoint) | < 500ms at p95 |
| NF-03 | Translation pipeline latency per item | < 5 seconds |
| NF-04 | Daily translation cost ceiling | $20/day |
| NF-05 | Feed freshness (max staleness) | 30 minutes |
| NF-06 | SQLite database size (with retention policy) | < 500 MB |
| NF-07 | Uptime target (Railway backend) | 99% monthly |
| NF-08 | Mobile viewport support | 320px - 428px width |
| NF-09 | Accessibility | WCAG 2.1 Level A minimum |
| NF-10 | Zero user data collection (no accounts, no tracking) | Hard constraint |

---

## 3. Rationale

### 3.1 Why Approach A (Translated Feed) over Social/Community

Approach A is the minimum viable product for a solo founder. A pure content consumption app avoids the cold-start problem of social features, eliminates moderation burden, and reduces the surface area to something one person can build in a week. Social features (comments, sharing, accounts) are deferred to post-PMF.

### 3.2 Why DeepSeek V3 for Translation

- **ACG domain quality**: DeepSeek V3 handles anime/manga/game terminology (e.g., isekai, shounen, gacha) far better than generic translation APIs (Google Translate, DeepL). As an LLM, it can infer context from surrounding text.
- **Cost efficiency**: DeepSeek V3 pricing is approximately $0.27/M input tokens and $1.10/M output tokens (as of 2026-04). At MVP scale (~200 items/day, ~300 tokens/item), daily cost is under $0.50, well within the $20 ceiling.
- **Chinese specialization**: DeepSeek is a Chinese AI company; their models produce more natural zh-CN output than Western alternatives.

### 3.3 Why FastAPI + SQLite

- **FastAPI**: Async-first, auto-generated OpenAPI docs, type-safe with Pydantic. Ideal for a small backend that primarily calls external APIs and serves JSON.
- **SQLite**: Zero-configuration, single-file database. For a solo-founder MVP with <10K rows/day, SQLite is more than sufficient. Eliminates the operational overhead of PostgreSQL. Can be migrated later if needed.
- **APScheduler**: In-process scheduler avoids the complexity of Celery/Redis for a simple 30-minute cron. If the scheduler proves insufficient, it can be swapped for an external cron trigger.

### 3.4 Why Next.js App Router + shadcn/ui

- **Next.js App Router**: Server components reduce client-side JavaScript. ISR (Incremental Static Regeneration) or on-demand revalidation can cache the feed at the edge. Vercel deployment is zero-configuration.
- **shadcn/ui**: Copy-paste component model (no dependency lock-in), built on Radix primitives for accessibility, Tailwind-first styling. Provides a polished look without a designer.
- **Tailwind CSS**: Utility-first, no context-switching between CSS files, responsive design via built-in breakpoints.

### 3.5 Why Vercel + Railway

- **Vercel**: Free tier supports hobby projects. Edge network ensures fast global delivery. GitHub integration enables preview deploys on every PR.
- **Railway**: Simpler than AWS/GCP for a solo founder. Supports persistent volumes for SQLite. Auto-deploys from GitHub. Free trial and low-cost hobby tier.

### 3.6 Why Chinese-Only (zh-CN) for MVP

The founder's target audience is Chinese-speaking. Supporting multiple languages adds UI complexity, increases translation costs linearly, and dilutes focus. Post-PMF, additional languages (ja, en, ko) can be added as a configuration layer.

---

## 4. Detailed Design

### 4.1 System Architecture

```
+------------------------------------------------------------------+
|                         DEPLOYMENT                                |
|                                                                   |
|  +---------------------------+    +----------------------------+  |
|  |    VERCEL (Frontend)      |    |    RAILWAY (Backend)       |  |
|  |                           |    |                            |  |
|  |  Next.js App Router       |    |  FastAPI Application       |  |
|  |  - Server Components      |--->|  - REST API endpoints      |  |
|  |  - shadcn/ui components   |    |  - APScheduler (cron)      |  |
|  |  - Tailwind CSS           |    |  - SQLite (persistent vol) |  |
|  |  - ISR / On-demand reval  |<---|  - Translation pipeline    |  |
|  |                           |    |                            |  |
|  +---------------------------+    +---------+------------------+  |
|                                             |                    |
+------------------------------------------------------------------+
                                              |
                              +---------------+----------------+
                              |                                |
                    +---------v----------+      +--------------v--------+
                    |   EXTERNAL APIS    |      |   DEEPSEEK V3 API     |
                    |                    |      |                        |
                    |  - Reddit JSON API |      |  POST /chat/completions|
                    |  - AniList GraphQL |      |  (translation calls)   |
                    |  - Steam Store API |      |                        |
                    |  - RSS feeds (JP)  |      +------------------------+
                    +--------------------+
```

### 4.2 Data Flow Diagram

```
                        CRON TRIGGER (every 30 min)
                                 |
                                 v
                    +------------------------+
                    |   FETCH ORCHESTRATOR   |
                    +------------------------+
                                 |
          +----------+-----------+-----------+----------+
          |          |                       |          |
          v          v                       v          v
   +------------+ +----------+        +----------+ +---------+
   |  REDDIT    | | ANILIST  |        |  STEAM   | | RSS JP  |
   |  FETCHER   | | FETCHER  |        | FETCHER  | | FETCHER |
   +------------+ +----------+        +----------+ +---------+
        |               |                  |            |
        v               v                  v            v
   +------------------------------------------------------------+
   |                    RAW ITEM QUEUE                           |
   |  (in-memory list of dicts, deduplicated by source_url)     |
   +------------------------------------------------------------+
                                 |
                                 v
                    +------------------------+
                    |  DEDUPLICATION FILTER  |
                    |  (check DB for         |
                    |   existing source_url) |
                    +------------------------+
                                 |
                                 v  (new items only)
                    +------------------------+
                    |  TRANSLATION PIPELINE  |
                    |  (batch call to        |
                    |   DeepSeek V3)         |
                    +------------------------+
                                 |
                                 v
                    +------------------------+
                    |  HEAT SCORE CALCULATOR |
                    |  (per-source formula)  |
                    +------------------------+
                                 |
                                 v
                    +------------------------+
                    |  DATABASE WRITE        |
                    |  (SQLite INSERT)       |
                    +------------------------+
                                 |
                                 v
                    +------------------------+
                    |  CACHE INVALIDATION    |
                    |  (notify frontend      |
                    |   to revalidate)       |
                    +------------------------+

=== USER REQUEST FLOW ===

  Browser ---> Vercel Edge CDN
                    |
                    | (cache miss or stale)
                    v
             Next.js Server Component
                    |
                    | GET /api/feed?sort=hot&sources=reddit,anilist
                    v
             Railway FastAPI Backend
                    |
                    | Query SQLite
                    v
             JSON Response (paginated)
                    |
                    v
             Server-rendered HTML cards
```

### 4.3 API Endpoint Design

#### Base URL: `https://api.acgfeed.example.com` (Railway)

#### Endpoints

```
GET /api/feed
  Query Parameters:
    - sort: "hot" (default) | "new"
    - sources: comma-separated list of source names
      (e.g., "reddit,anilist") -- omit for all sources
    - page: integer, default 1
    - per_page: integer, default 20, max 50

  Response 200:
    {
      "items": [
        {
          "id": "uuid",
          "source": "reddit",
          "source_url": "https://reddit.com/r/anime/...",
          "translated_title": "...",
          "translated_body": "...",
          "heat_score": 42.7,
          "source_metadata": {
            "subreddit": "anime",
            "upvotes": 1234,
            "comment_count": 89
          },
          "fetched_at": "2026-04-09T10:30:00Z",
          "translated_at": "2026-04-09T10:30:05Z"
        }
      ],
      "total": 150,
      "page": 1,
      "per_page": 20,
      "has_next": true
    }

GET /api/feed/{item_id}
  Response 200:
    {
      "id": "uuid",
      "source": "anilist",
      "source_url": "https://anilist.co/...",
      "original_title": "Jujutsu Kaisen...",
      "translated_title": "...",
      "original_body": "...",
      "translated_body": "...",
      "heat_score": 88.2,
      "source_metadata": { ... },
      "fetched_at": "2026-04-09T10:30:00Z",
      "translated_at": "2026-04-09T10:30:04Z",
      "language": "zh-CN"
    }

  Response 404:
    { "detail": "Feed item not found" }

GET /api/sources
  Response 200:
    {
      "sources": [
        { "name": "reddit", "label": "Reddit", "enabled": true },
        { "name": "anilist", "label": "AniList", "enabled": true },
        { "name": "steam", "label": "Steam", "enabled": true },
        { "name": "anime_news", "label": "Anime News (JP)", "enabled": true }
      ]
    }

GET /api/health
  Response 200:
    {
      "status": "healthy",
      "last_fetch_at": "2026-04-09T10:30:00Z",
      "total_items": 1234,
      "db_size_mb": 12.5
    }

POST /api/admin/trigger-fetch  (optional, for manual fetch triggers)
  Headers: X-Admin-Key: <shared secret>
  Response 200:
    { "status": "fetch_triggered", "job_id": "..." }
```

#### Pydantic Models

```python
class SourceEnum(str, Enum):
    reddit = "reddit"
    anilist = "anilist"
    steam = "steam"
    anime_news = "anime_news"

class FeedItemBase(BaseModel):
    source: SourceEnum
    source_url: str
    original_title: str
    translated_title: str
    original_body: str
    translated_body: str
    heat_score: float
    source_metadata: dict
    language: str = "zh-CN"

class FeedItem(FeedItemBase):
    id: str
    fetched_at: datetime
    translated_at: datetime

class FeedResponse(BaseModel):
    items: list[FeedItem]
    total: int
    page: int
    per_page: int
    has_next: bool
```

### 4.4 Cron Job Workflow

```
APScheduler (BackgroundScheduler)
  - Job: fetch_all_sources
  - Trigger: interval, every 30 minutes
  - Jitter: 0-60 seconds (stagger to avoid thundering herd)
```

#### Workflow Steps

1. **Trigger**: APScheduler fires `fetch_all_sources` every 30 minutes.

2. **Fetch Phase** (parallel, via asyncio.gather):
   - `fetch_reddit()`: GET Reddit JSON API for r/anime, r/manga, r/Games hot posts (top 25 each). OAuth2 token refresh if expired. Extract title, selftext (truncated to 500 chars), upvotes, comment_count, permalink.
   - `fetch_anilist()`: POST AniList GraphQL query for trending media (anime + manga), top 25. Extract title (romaji/native), description (truncated), trending score, siteUrl.
   - `fetch_steam()`: GET Steam Store API for top sellers + Steam RSS for news. Extract name, short_description, review_count, header_image, store_url.
   - `fetch_rss()`: Parse Japanese anime news RSS feeds (Anime! Anime!, MANTANWEB). Extract title, description, link, pubDate.

3. **Deduplication**: For each raw item, query SQLite by `source_url`. Skip if already exists.

4. **Translation Phase** (batch, via DeepSeek V3):
   - Collect all new items into a batch.
   - Construct translation prompt for each item:
     ```
     System: You are a professional translator specializing in ACG
     (Anime, Comic, Games) content. Translate the following text to
     simplified Chinese (zh-CN). Preserve proper nouns using accepted
     Chinese transliterations where they exist (e.g., "Jujutsu Kaisen"
     -> "咒术回战"). For terms without established translations,
     keep the original in parentheses.

     User: Title: {original_title}
     Body: {original_body}
     ```
   - Batch up to 10 items per API call to reduce round-trips.
   - Parse response, split translations back to individual items.

5. **Scoring Phase**: Calculate heat_score for each item and store it. The score is recalculated at query time for up-to-date ranking:
   - Reddit: `(upvotes ^ 0.7) * (1 / (1 + hours_since_fetch / 24))`
   - AniList: `(trending_score ^ 0.7) * (1 / (1 + hours_since_fetch / 24))`
   - Steam: `(review_count ^ 0.7) * (1 / (1 + hours_since_fetch / 24))`
   - RSS: `1.0 * (1 / (1 + hours_since_fetch / 12))` (recency-only)

   **Note**: The stored `heat_score` is used as an initial sort key (with SQL index). At query time, the application recalculates the score using current time for accurate recency decay on the fetched items, then re-sorts in application code.

6. **Storage Phase**: INSERT all new items into SQLite `feed_items` table.

7. **Cache Invalidation**: Set a flag or update a timestamp that the frontend can poll/check. Alternatively, if using Next.js on-demand revalidation, call the Vercel revalidation webhook.

#### SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS feed_items (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL CHECK(source IN ('reddit', 'anilist', 'steam', 'anime_news')),
    source_url TEXT NOT NULL UNIQUE,
    original_title TEXT NOT NULL,
    translated_title TEXT NOT NULL,
    original_body TEXT NOT NULL,
    translated_body TEXT NOT NULL,
    heat_score REAL NOT NULL DEFAULT 0.0,
    source_metadata TEXT NOT NULL DEFAULT '{}',  -- JSON string
    fetched_at TEXT NOT NULL,                      -- ISO 8601
    translated_at TEXT NOT NULL,                   -- ISO 8601
    language TEXT NOT NULL DEFAULT 'zh-CN'
);

CREATE INDEX idx_feed_items_heat ON feed_items(heat_score DESC);
CREATE INDEX idx_feed_items_fetched ON feed_items(fetched_at DESC);
CREATE INDEX idx_feed_items_source ON feed_items(source);
CREATE INDEX idx_feed_items_source_url ON feed_items(source_url);

-- Metadata table for cron tracking
CREATE TABLE IF NOT EXISTS system_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- Stores: last_fetch_at, last_fetch_status, etc.
```

### 4.5 Translation Pipeline (DeepSeek V3 Integration)

#### Configuration

```python
DEEPSEEK_API_URL = "https://api.deepseek.com"  # Use OpenAI client with this base_url
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek V3
TRANSLATION_BATCH_SIZE = 10       # items per API call
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 3, 5]        # seconds
```

#### Translation Flow

```
New items (deduplicated)
         |
         v
  Group into batches of 10
         |
         v  (for each batch)
  Build multi-item prompt:
  ┌────────────────────────────────────────────┐
  │ System: You are a professional ACG         │
  │ translator...                              │
  │                                            │
  │ Translate each item. Respond in JSON:      │
  │ [{"id": "...", "title": "...", "body":     │
  │   "..."}, ...]                             │
  │                                            │
  │ Item 1:                                    │
  │ Title: ...                                 │
  │ Body: ...                                  │
  │                                            │
  │ Item 2:                                    │
  │ Title: ...                                 │
  │ Body: ...                                  │
  └────────────────────────────────────────────┘
         |
         v
  POST /v1/chat/completions
  - model: deepseek-chat
  - temperature: 0.3 (low for translation)
  - response_format: { type: "json_object" }
  - max_tokens: 2048
         |
         v
  Parse JSON response
         |
         v  (on failure)
  Retry with exponential backoff (up to 3x)
         |
         v  (on permanent failure)
  Log error, store item with original text,
  mark translated_title/translated_body as
  original text with [TRANSLATION_PENDING] prefix
```

#### Cost Estimation

| Metric | Value |
|--------|-------|
| Items per fetch cycle | ~50-75 (25 Reddit x3 subreddits, 25 AniList, 10-25 Steam, 10-20 RSS) |
| New items per cycle (after dedup) | ~15-30 |
| Tokens per item (input + output) | ~400 |
| API calls per day (48 cycles) | ~48-96 |
| Tokens per day | ~7,200 - 14,400 |
| Estimated daily cost | $0.02 - $0.05 (well under $20 cap) |

### 4.6 Frontend Component Structure

```
app/
  layout.tsx              -- Root layout: font, metadata, global styles
  page.tsx                -- Home page: server component, fetches /api/feed
  api/
    revalidate/
      route.ts            -- Webhook endpoint for on-demand ISR revalidation

components/
  layout/
    TopBar.tsx            -- Logo, source filter checkboxes, sort toggle
    TabBar.tsx            -- Feed (active), Social (disabled), Search (disabled)

  feed/
    FeedList.tsx          -- Container: fetches data, handles pagination
    FeedCard.tsx          -- Individual card component
    SourceBadge.tsx       -- Colored badge for source type
    HeatScore.tsx         -- Heat score display (number + flame icon)
    ViewOriginal.tsx      -- Collapsible link to source URL
    EmptyState.tsx        -- Shown when no items match filters
    LoadingSkeleton.tsx   -- Card-shaped skeleton for loading state

  ui/                     -- shadcn/ui primitives (auto-generated)
    button.tsx
    card.tsx
    checkbox.tsx
    skeleton.tsx
    toggle.tsx

lib/
  api.ts                  -- Fetch helper for backend API
  types.ts                -- TypeScript interfaces matching Pydantic models
  constants.ts            -- Source labels, colors, sort options
```

#### Component Details

**TopBar.tsx**
- Props: `sources: SourceConfig[]`, `activeSort: "hot" | "new"`, `activeSources: string[]`
- Renders: Logo left, source checkboxes center, hot/new toggle right
- Mobile: Checkbox labels collapse to icons on small screens

**FeedCard.tsx**
- Props: `item: FeedItem`
- Layout:
  ```
  ┌────────────────────────────────────────┐
  │                          [Reddit badge]│
  │                                        │
  │  **Translated title goes here**        │
  │                                        │
  │  Translated body excerpt spanning      │
  │  two to three lines of text before     │
  │  being truncated with an ellipsis...   │
  │                                        │
  │  🔥 42.7  ·  2 hours ago              │
  │  ▸ View original (collapsible)         │
  └────────────────────────────────────────┘
  ```
- Styling: shadcn Card with rounded-lg, shadow-sm, hover:shadow-md transition
- Responsive: Full-width on mobile, max-w-2xl mx-auto on desktop

**FeedList.tsx**
- Fetches from `/api/feed?sort={sort}&sources={sources}&page={page}`
- Renders list of FeedCard components
- Implements infinite scroll (Intersection Observer) or "Load more" button
- Shows LoadingSkeleton during fetch
- Shows EmptyState when no items match filters

**TabBar.tsx**
- Three tabs: Feed (active, clickable), Social (disabled, grayed), Search (disabled, grayed)
- Tooltip on disabled tabs: "Coming soon"

### 4.7 Error Handling Strategy

#### Backend Error Handling

| Error Type | Handling |
|------------|----------|
| External API timeout (Reddit, AniList, Steam, RSS) | Skip source for this cycle, log warning, continue with other sources. Next cycle retries. |
| External API rate limit (HTTP 429) | Exponential backoff per source. Reddit OAuth token refresh. Log and skip if persistent. |
| External API auth failure (Reddit OAuth) | Alert via log (no user impact). Skip Reddit for this cycle. |
| DeepSeek API failure | Retry up to 3 times with backoff. On permanent failure, store item with original text prefixed with `[TRANSLATION_PENDING]`. |
| DeepSeek returns malformed JSON | Retry once with stricter prompt. On second failure, fall back to individual item translation. |
| SQLite write failure | Log error with full context. This is a critical failure -- alert. Items are lost for this cycle but will be re-fetched next cycle if not already present. |
| Duplicate source_url | Silently skip (expected behavior, not an error). |

#### Frontend Error Handling

| Error Type | Handling |
|------------|----------|
| API network error | Show toast: "Unable to load feed. Tap to retry." with retry button. |
| API returns empty list | Show EmptyState component with message: "No items found. Try adjusting your filters." |
| API returns 5xx | Same as network error. Logged in Vercel analytics. |
| Slow loading (>3s) | Show LoadingSkeleton. If >10s, show message: "Taking longer than usual..." |
| Stale data (>30 min old) | Timestamp on each card shows actual age. No special treatment needed. |

#### Logging

- Backend: Python `logging` module. Structured JSON logs to stdout (Railway captures these).
- Frontend: Next.js built-in logging. Errors reported to Vercel dashboard.
- Log levels: ERROR for failures that lose data, WARNING for skipped sources, INFO for cron start/end and item counts.

### 4.8 Data Retention Policy

| Data Type | Retention Period | Cleanup Method |
|-----------|-----------------|----------------|
| Feed items | 7 days | APScheduler job runs daily: `DELETE FROM feed_items WHERE fetched_at < datetime('now', '-7 days')` |
| System metadata | Indefinite | Small key-value pairs, negligible storage |
| Translation logs | 7 days | Log rotation on Railway (default behavior) |
| Failed fetch records | 30 days | Optional: separate table for fetch failures, cleaned weekly |

**Rationale**: 7 days keeps the feed focused on fresh content. At ~200 new items/day, 7 days = ~1,400 active rows. Each row averages ~1 KB = ~1.4 MB total, well within limits. Retention period is configurable via `RETENTION_DAYS` env var.

---

## 5. Design Documents

The following supporting documents provide additional detail for specific aspects of this design:

| Document | Path | Description |
|----------|------|-------------|
| BDD Specifications | `bdd-specs.md` | Behavior-driven development scenarios for all user-facing features and cron jobs |
| Architecture | `architecture.md` | Detailed system architecture, deployment topology, and infrastructure configuration |
| Best Practices | `best-practices.md` | Coding standards, naming conventions, testing strategy, and review checklist |

> Note: These documents are companions to this `_index.md`. This document is the authoritative source for requirements and design decisions.

---

## Appendix A: Environment Variables

### Backend (Railway)

```
DEEPSEEK_API_KEY=sk-...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=acgfeed/1.0
DATABASE_PATH=/data/acgfeed.db
ADMIN_API_KEY=...                    # For manual fetch triggers
FRONTEND_URL=https://acgfeed.vercel.app  # CORS origin
LOG_LEVEL=INFO
```

### Frontend (Vercel)

```
NEXT_PUBLIC_API_URL=https://acgfeed-backend.up.railway.app
REVALIDATION_SECRET=...              # For on-demand ISR webhook
```

## Appendix B: Key Dependencies

### Backend

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | ^0.110+ | Web framework |
| uvicorn | ^0.29+ | ASGI server |
| apscheduler | ^3.10+ | In-process cron scheduler |
| httpx | ^0.27+ | Async HTTP client for external APIs |
| pydantic | ^2.0+ | Data validation and serialization |
| pydantic-settings | ^2.0+ | Settings management from env vars |
| feedparser | ^6.0+ | RSS/Atom feed parsing |
| aiosqlite | ^0.20+ | Async SQLite driver |

### Frontend

| Package | Version | Purpose |
|---------|---------|---------|
| next | ^14.0+ | React framework (App Router) |
| react | ^18.0+ | UI library |
| tailwindcss | ^3.4+ | Utility-first CSS |
| @radix-ui/* | latest | Accessible UI primitives (via shadcn/ui) |
| lucide-react | latest | Icon library |
| clsx + tailwind-merge | latest | Conditional classnames |

## Appendix C: Reddit OAuth2 Flow

```
1. POST https://www.reddit.com/api/v1/access_token
   - grant_type=client_credentials
   - Authorization: Basic base64(client_id:client_secret)
   - Response: { "access_token": "...", "expires_in": 3600 }

2. Cache token in memory (valid for 1 hour).

3. GET https://oauth.reddit.com/r/anime/hot?limit=25
   - Authorization: Bearer {access_token}
   - User-Agent: {REDDIT_USER_AGENT}

4. On 401 response: refresh token and retry.
```
