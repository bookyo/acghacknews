# ACG Feed - Best Practices

> Categorized best practices for security, performance, error handling, and translation quality.
> Last updated: 2026-04-09 | Status: Pre-implementation

---

## 1. Security

### 1.1 API Key Management

- **Never commit secrets to version control.** Store all API keys (DeepSeek, Reddit client ID/secret, admin key) in environment variables. Use `.env` files locally (gitignored) and platform environment variables (Railway, Vercel) in production.
- **Use a single `.env.example` file** checked into version control with placeholder values to document required variables. Never include actual keys.
- **Rotate keys on a schedule.** Plan to rotate the DeepSeek API key and admin key quarterly. Keep the old key valid for a grace period during rotation.
- **Restrict the admin endpoint.** The `POST /api/admin/trigger-fetch` endpoint must validate the `X-Admin-Key` header against the `ADMIN_API_KEY` environment variable. Return 401 on mismatch. Never expose this endpoint publicly.
- **Do not log API keys.** Ensure that log statements never include full API keys. If logging request details, mask keys (e.g., `sk-...abc`).

### 1.2 Input Sanitization

- **Validate all query parameters** at the API boundary using Pydantic models. Reject unexpected values with 422 Unprocessable Entity.
- **Whitelist allowed values.** The `sources` parameter only accepts `reddit`, `anilist`, `steam`, `anime_news`. The `sort` parameter only accepts `hot`, `new`. Reject anything else.
- **Clamp pagination parameters.** `per_page` must be clamped to max 50. `page` must be >= 1. Negative or zero values are rejected.
- **Sanitize RSS content.** RSS feed content may contain HTML. Strip all HTML tags before storage and translation using `bleach` or `html2text`. Never render raw HTML from external sources.
- **URL validation.** The `source_url` field must be validated as a valid URL with an allowed scheme (http/https only). Reject javascript: or data: URLs.

### 1.3 CORS and Rate Limiting

- **Configure CORS strictly.** Set `allow_origins` to the exact frontend URL (e.g., `https://acgfeed.vercel.app`). Do not use `allow_origins=["*"]` in production.
- **Implement server-side rate limiting.** Use a simple in-memory rate limiter (e.g., `slowapi` or a custom middleware) to protect the feed endpoint. Suggested limits:
  - `GET /api/feed`: 60 requests per minute per IP
  - `GET /api/health`: 120 requests per minute per IP
  - `POST /api/admin/*`: 10 requests per minute per IP
- **Add security headers.** Include standard headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy: default-src 'self'`
  - `Referrer-Policy: strict-origin-when-cross-origin`

### 1.4 Data Privacy

- **Zero user data collection.** The MVP has no user accounts, no cookies, no analytics tracking beyond server logs. Ensure no user-identifying data is stored.
- **No third-party scripts.** Do not include Google Analytics, Facebook Pixel, or other third-party tracking scripts in the frontend. If analytics are needed later, use a privacy-respecting solution (e.g., Plausible, Umami).
- **Log minimally.** Server logs should contain only operational data (timestamps, error messages, source names). Never log full article content or user IP addresses beyond rate limiting.

---

## 2. Performance

### 2.1 SQLite Optimization

- **Use WAL mode.** Enable Write-Ahead Logging for better concurrent read performance:
  ```python
  connection.execute("PRAGMA journal_mode=WAL")
  ```
- **Set synchronous to NORMAL.** Balance between safety and speed:
  ```python
  connection.execute("PRAGMA synchronous=NORMAL")
  ```
- **Create proper indexes.** Ensure indexes exist for all query patterns:
  - `feed_items(heat_score DESC)` for hot sorting
  - `feed_items(fetched_at DESC)` for new sorting
  - `feed_items(source)` for source filtering
  - `feed_items(source_url)` for deduplication lookups (UNIQUE constraint)
- **Use covering indexes where possible.** For the main feed query, include all selected columns in the index to avoid table lookups.
- **Batch inserts.** Use `executemany` or a single transaction for inserting multiple items:
  ```python
  with connection:
      connection.executemany(INSERT_SQL, items)
  ```
- **Vacuum periodically.** Run `VACUUM` after large deletions (cleanup job) to reclaim disk space and optimize the database file.
- **Connection pooling.** Use a single connection with proper threading, or a small connection pool. For FastAPI with async, use `aiosqlite` with a connection managed per-request.

### 2.2 Pagination

- **Use LIMIT/OFFSET pagination.** At MVP scale (<10K rows), LIMIT/OFFSET is sufficient. For larger datasets, consider keyset pagination (WHERE id < last_seen_id).
- **Default to 20 items per page.** 50 is the max. Smaller pages load faster and reduce bandwidth.
- **Return total count.** Include `total` in the response so the frontend knows if more pages exist. Use a separate `SELECT COUNT(*)` or cache the count.
- **Avoid counting on every request.** Cache the total count in `system_metadata` and update it after each fetch cycle and cleanup.

### 2.3 Caching

- **HTTP cache headers.** Set `Cache-Control: max-age=300` (5 minutes) on the feed endpoint. This allows Vercel's CDN to cache responses without stale data exceeding the 30-minute fetch cycle.
- **ETag support.** Generate an ETag from the latest `fetched_at` timestamp. Clients can send `If-None-Match` to avoid re-downloading unchanged data.
- **Next.js ISR.** Use Incremental Static Regeneration with a 5-minute revalidation period. Trigger on-demand revalidation when the backend completes a fetch cycle.
- **Cache DeepSeek system prompt.** The system prompt is identical across all translation calls. DeepSeek's context caching automatically reduces input cost by 90% for cached prefixes. Ensure the system prompt is sent as the first message in every request.
- **In-memory source URL cache.** Maintain a small in-memory set of the last 1000 source_urls to avoid database lookups for deduplication. Refresh from DB on startup.

### 2.4 Frontend Performance

- **Server-side rendering.** Use Next.js Server Components for the initial page load. The first 20-50 cards render as HTML, no client-side JavaScript required.
- **Infinite scroll with Intersection Observer.** Load subsequent pages only when the user scrolls near the bottom. Do not preload all pages.
- **Skeleton loading states.** Show card-shaped skeletons during data fetching. Avoid layout shifts (CLS) by giving skeletons the same dimensions as real cards.
- **Image optimization.** If displaying cover images (AniList, Steam), use Next.js `<Image>` component with lazy loading and proper sizing.
- **Minimize client-side JavaScript.** Use Server Components where possible. Keep interactive components (filter checkboxes, sort toggle) as small Client Components.

---

## 3. Error Handling

### 3.1 Retry with Exponential Backoff

- **Standard retry pattern.** For all external API calls (Reddit, AniList, Steam, DeepSeek, RSS):
  ```
  Attempt 1: Immediate
  Attempt 2: Wait 1 second
  Attempt 3: Wait 3 seconds
  Attempt 4: Wait 5 seconds (final attempt)
  ```
- **Jitter on retry.** Add random jitter of +/- 500ms to each retry delay to avoid synchronized retry storms.
- **Differentiate retryable vs. non-retryable errors:**
  - Retryable: HTTP 429, 500, 502, 503, 504, network timeout
  - Non-retryable: HTTP 400, 401, 403, 404
- **Per-source isolation.** A failure in one source must not block or affect other sources. Each fetcher runs independently and catches its own exceptions.

### 3.2 Graceful Degradation

- **Missing source.** If one source fails, the feed continues to display items from other sources. The source filter still shows all sources, but no new items from the failed source appear.
- **Translation failure.** Items without translation show the original text with a "Translation pending" badge. The user can still see and access the content.
- **Database failure.** If SQLite becomes unavailable, the API returns 503 Service Unavailable. The frontend shows a "Service temporarily unavailable" message with a retry option.
- **All sources fail.** The system keeps existing data unchanged. The feed continues to serve stale (but valid) items. The health endpoint reflects the degraded state.

### 3.3 Logging Standards

- **Structured logging.** Use JSON-formatted logs for machine readability:
  ```python
  logger.info("Fetch cycle completed", extra={
      "sources_fetched": 4,
      "sources_failed": 0,
      "new_items": 23,
      "duplicates_skipped": 5,
      "duration_seconds": 12.3,
  })
  ```
- **Log levels:**
  - ERROR: Data loss (translation permanently failed, database write failed)
  - WARNING: Degraded service (source skipped, retry succeeded)
  - INFO: Normal operations (fetch cycle start/end, item counts)
  - DEBUG: Detailed request/response data (disabled in production)
- **Log correlation.** Each fetch cycle gets a unique `cycle_id`. All log messages within a cycle include this ID for easy filtering.
- **Error context.** Always log the source name, HTTP status code, and error message when a fetcher fails.

### 3.4 Circuit Breaker Pattern

- **Per-source circuit breaker.** Track consecutive failures per source. After 5 consecutive failures:
  - Trip the circuit: stop attempting to fetch from that source for 1 hour
  - Log a WARNING that the circuit is open
  - After 1 hour, attempt one request (half-open state)
  - If it succeeds, close the circuit; if it fails, keep open for another hour
- **Prevents wasted resources.** Avoids hammering a dead API with repeated requests every 30 minutes.

---

## 4. Translation Quality

### 4.1 Prompt Engineering for ACG Terminology

- **System prompt design.** The system prompt must include:
  ```
  You are a professional translator specializing in ACG (Anime, Comic, Games)
  content. Translate the following text to simplified Chinese (zh-CN).

  Rules:
  1. Use the established Chinese name for well-known anime/manga titles.
     Examples: "Jujutsu Kaisen" -> "咒术回战", "One Piece" -> "海贼王",
     "Attack on Titan" -> "进击的巨人", "Demon Slayer" -> "鬼灭之刃",
     "My Hero Academia" -> "我的英雄学院"
  2. Keep character names in their accepted Chinese forms where known.
  3. For Japanese titles/names without established Chinese translations,
     provide a transliteration and keep the original in parentheses.
     Example: "新番标题" (Shinban Taitoru)
  4. Preserve technical gaming terminology in English when no standard
     Chinese equivalent exists (e.g., "FPS", "DLC", "buff", "nerf").
  5. Maintain the tone and register of the original. Reddit discussions
     should sound casual; news articles should sound formal.
  6. Keep markdown formatting, links, and special characters intact.
  7. Respond in JSON format: {"title": "...", "body": "..."}
  ```
- **Low temperature.** Use `temperature=0.3` for translation. Lower temperature produces more consistent, deterministic translations. Avoid `temperature=0` as some models produce degenerate outputs at that setting.
- **Max tokens.** Set `max_tokens=2048` for batch translations. The average item body is 500 characters (roughly 250 tokens), so 2048 output tokens is sufficient for a batch of 10 items.

### 4.2 ACG Terminology Consistency

- **Maintain a terminology glossary.** Create a JSON file mapping common English/Japanese ACG terms to their Chinese equivalents. Include this in the system prompt or as a reference.
  ```json
  {
    "Jujutsu Kaisen": "咒术回战",
    "One Piece": "海贼王",
    "Attack on Titan": "进击的巨人",
    "Demon Slayer": "鬼灭之刃",
    "isekai": "异世界",
    "shounen": "少年向",
    "shoujo": "少女向",
    "gacha": "抽卡",
    "light novel": "轻小说"
  }
  ```
- **Update the glossary regularly.** When new anime seasons start, add new title mappings. This is a manual process but ensures consistency.
- **Context caching benefit.** Since the system prompt (including terminology rules) is the same across all requests, DeepSeek's context caching automatically applies, reducing cost by 90% for the system prompt portion.

### 4.3 Translation Quality Assurance

- **Log translation pairs.** Store both original and translated text. Periodically review a sample of translations to identify quality issues.
- **Length validation.** The translated text should be roughly similar in length to the original (within 50-150% range). If the translation is much shorter or longer, it may indicate an error.
- **JSON response validation.** Always validate that the DeepSeek response contains valid JSON with the expected keys. If the response is not valid JSON, retry with a stricter prompt or fall back to single-item translation.
- **Fallback strategy.** If batch translation fails, fall back to translating items one at a time. This isolates failures to individual items rather than losing an entire batch.

### 4.4 Translation Cost Optimization

- **Truncate before translation.** Original body text is already truncated to 500 characters before storage. This keeps per-item token count low.
- **Batch multiple items.** Sending 10 items per API call reduces overhead (system prompt sent once instead of 10 times).
- **Context caching.** DeepSeek caches the system prompt prefix. After the first request, subsequent requests with the same prompt cost 90% less for the input portion.
- **Skip already-translated items.** Deduplication ensures each item is translated only once.
- **Cache miss pricing.** At cache miss pricing ($0.28/1M input, $0.42/1M output), translating 200 items/day costs approximately $0.03/day. With caching, it is even less.

### 4.5 Japanese-Specific Translation Considerations

- **RSS content may contain mixed Japanese text.** Japanese anime news articles use kanji, hiragana, and katakana. DeepSeek V3 handles Japanese-to-Chinese translation well due to shared kanji roots.
- **Honorifics.** Japanese text may include honorifics (-san, -kun, -sensei). In Chinese translation, these are typically preserved or adapted to Chinese equivalents (先生, 老师).
- **Date formats.** Japanese RSS feeds may use Japanese date formats (2026年4月9日). Ensure these are handled correctly in translation and parsing.

---

## 5. Code Quality

### 5.1 Project Structure

```
backend/
  app/
    __init__.py
    main.py              # FastAPI app, lifespan, middleware
    config.py            # Settings via pydantic-settings
    models.py            # Pydantic models
    database.py          # SQLite connection, schema init
    routers/
      feed.py            # GET /api/feed, /api/feed/{id}
      sources.py         # GET /api/sources
      health.py          # GET /api/health
      admin.py           # POST /api/admin/trigger-fetch
    services/
      fetcher.py         # BaseFetcher + orchestrator
      reddit.py          # RedditFetcher
      anilist.py         # AniListFetcher
      steam.py           # SteamFetcher
      rss.py             # RSSFetcher
      translation.py     # TranslationService
      scoring.py         # Heat score calculation
    repository.py        # Database queries
  tests/
    test_fetchers.py
    test_translation.py
    test_scoring.py
    test_api.py
  pyproject.toml

frontend/
  app/
    layout.tsx
    page.tsx
  components/
    layout/
    feed/
    ui/
  lib/
    api.ts
    types.ts
    constants.ts
  next.config.js
  package.json
```

### 5.2 Testing Strategy

- **Unit tests.** Test each fetcher, the translation service, and scoring in isolation. Mock external HTTP calls using `respx` or `pytest-httpx`.
- **Integration tests.** Test the full fetch-translate-store pipeline with a test SQLite database.
- **API tests.** Test the FastAPI endpoints using `httpx.AsyncClient` with the TestClient transport.
- **Translation quality tests.** Include a small set of known translations as assertions:
  ```python
  def test_anime_title_translation():
      result = translate("Jujutsu Kaisen Season 3 Announced")
      assert "咒术回战" in result
  ```
- **Run tests on CI.** Configure GitHub Actions to run tests on every push.

### 5.3 Configuration Management

- **Use pydantic-settings.** Load all configuration from environment variables with type validation:
  ```python
  from pydantic_settings import BaseSettings

  class Settings(BaseSettings):
      deepseek_api_key: str
      reddit_client_id: str
      reddit_client_secret: str
      reddit_user_agent: str = "acgfeed/1.0"
      database_path: str = "/data/acgfeed.db"
      admin_api_key: str
      frontend_url: str
      log_level: str = "INFO"
      fetch_interval_minutes: int = 30
      retention_days: int = 7

      class Config:
          env_file = ".env"
  ```
- **Fail fast on missing config.** If required environment variables are missing, the application should fail to start with a clear error message listing the missing variables.

### 5.4 Dependency Management

- **Pin dependencies.** Use `pyproject.toml` with exact version pins for production dependencies. This prevents surprise breakage from minor version bumps.
- **Minimal dependencies.** The backend stack is intentionally small: FastAPI, httpx, feedparser, apscheduler, pydantic, openai. Each additional dependency is a maintenance cost.
- **Regular updates.** Schedule monthly dependency updates. Run tests after updating.
