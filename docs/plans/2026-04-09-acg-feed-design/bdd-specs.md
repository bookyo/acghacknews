# ACG Feed - BDD Specifications

> Behavior-driven development scenarios for all user-facing features and cron jobs.
> Last updated: 2026-04-09 | Status: Pre-implementation

---

## Feature: Feed Aggregation

### Background

```gherkin
Background:
  Given the system is running
  And the APScheduler is configured to trigger every 30 minutes
```

### Scenario: Fetch posts from all sources successfully

```gherkin
Scenario: Fetch posts from all sources successfully (happy path)
  Given all external APIs (Reddit, AniList, Steam, RSS feeds) are available
  And the last fetch cycle completed 30 minutes ago
  When the scheduler triggers a new fetch cycle
  Then the system fetches posts from Reddit (r/anime, r/manga, r/Games) in parallel
  And the system fetches trending anime and manga from AniList
  And the system fetches top sellers and new releases from Steam
  And the system fetches articles from Anime! Anime! and MANTANWEB RSS feeds
  And all raw items are collected into an in-memory queue
  And the deduplication filter removes items with existing source_urls
  And new items are sent to the translation pipeline
  And heat scores are calculated for each new item
  And new items are inserted into the SQLite database
  And the cache is invalidated for the frontend
```

### Scenario: Reddit API is down (skip and retry)

```gherkin
Scenario: Reddit API is down
  Given the Reddit API returns HTTP 500 or times out
  And the AniList, Steam, and RSS APIs are available
  When the scheduler triggers a new fetch cycle
  Then the system logs a WARNING "Reddit API unavailable, skipping"
  And the system continues fetching from AniList, Steam, and RSS feeds
  And items from AniList, Steam, and RSS are processed normally
  And the Reddit fetcher will retry on the next 30-minute cycle
```

### Scenario: AniList API is down

```gherkin
Scenario: AniList API is down
  Given the AniList GraphQL endpoint returns an error or times out
  And Reddit, Steam, and RSS APIs are available
  When the scheduler triggers a new fetch cycle
  Then the system logs a WARNING "AniList API unavailable, skipping"
  And the system continues fetching from Reddit, Steam, and RSS feeds
  And items from Reddit, Steam, and RSS are processed normally
```

### Scenario: Duplicate detection by source_url

```gherkin
Scenario: Duplicate detection by source_url
  Given the database contains a feed item with source_url "https://reddit.com/r/anime/comments/abc123"
  When the Reddit fetcher returns an item with the same source_url
  Then the deduplication filter detects the duplicate
  And the duplicate item is skipped without error
  And no duplicate entry is created in the database
  And the system logs an INFO message noting the skip count
```

### Scenario: All sources fail

```gherkin
Scenario: All sources fail
  Given all external APIs (Reddit, AniList, Steam, RSS) return errors or time out
  When the scheduler triggers a new fetch cycle
  Then the system logs an ERROR "All sources failed in this cycle"
  And no new items are inserted into the database
  And existing feed items remain unchanged and available
  And the next 30-minute cycle retries all sources normally
  And the health endpoint (/api/health) reflects the failed fetch status
```

### Scenario: Partial source failure with retry

```gherkin
Scenario: Partial source failure with retry
  Given the Steam API returns HTTP 429 (rate limited)
  And Reddit, AniList, and RSS APIs are available
  When the fetch cycle runs
  Then the Steam fetcher waits 30 seconds and retries once
  And if the retry succeeds, Steam items are processed normally
  And if the retry fails, the Steam fetcher is skipped for this cycle
  And items from Reddit, AniList, and RSS are processed regardless
```

### Scenario: Fetch cycle timing

```gherkin
Scenario: Fetch cycle runs every 30 minutes with jitter
  Given the APScheduler is configured with interval trigger of 30 minutes
  And jitter is set to 0-60 seconds
  When the system starts
  Then the first fetch cycle runs at startup
  And subsequent cycles run approximately every 30 minutes
  And each cycle start time is jittered by 0-60 seconds
  And the system_metadata table records last_fetch_at and last_fetch_status
```

---

## Feature: Translation

### Background

```gherkin
Background:
  Given new feed items have been collected and deduplicated
  And the items have not yet been translated
```

### Scenario: Translate title and body to zh-CN via DeepSeek V3 (happy path)

```gherkin
Scenario: Translate title and body to zh-CN (happy path)
  Given the DeepSeek API is available
  And there are 15 new items to translate
  When the translation pipeline processes the items
  Then items are grouped into batches of up to 10
  And each batch is sent as a single API call to DeepSeek V3
  And the system prompt instructs ACG-aware translation to zh-CN
  And the response is parsed as JSON with "title" and "body" fields
  And each item's translated_title and translated_body are populated
  And the translated_at timestamp is set to the current time
```

### Scenario: Translation API rate limited

```gherkin
Scenario: Translation API rate limited
  Given the DeepSeek API returns HTTP 429 on the first attempt
  When the translation pipeline processes a batch
  Then the system waits 60 seconds and retries once
  And if the retry succeeds, translations are processed normally
  And if the retry fails, the system retries up to 2 more times with exponential backoff
  And if all retries are exhausted, the batch is marked as translation failed
```

### Scenario: ACG-specific terminology translation

```gherkin
Scenario: ACG-specific terminology (anime titles)
  Given an item with original_title "Jujutsu Kaisen Season 3 Announced"
  And an item with original_title "One Piece Chapter 1120 Discussion"
  And an item with original_title "Oshi no Ko manga ending confirmed"
  When the translation pipeline processes these items
  Then "Jujutsu Kaisen" is translated to "咒术回战"
  And "One Piece" is translated to "海贼王"
  And "Oshi no Ko" is translated to "我推的孩子"
  And season numbers, chapter numbers, and other numeric references are preserved
  And the system prompt includes a reminder to use established Chinese transliterations
```

### Scenario: ACG terminology without established translation

```gherkin
Scenario: ACG terminology without established Chinese translation
  Given an item with original_title referencing a niche game "VTuber no RPG"
  When the translation pipeline processes this item
  Then the title is translated to Chinese
  And terms without established translations keep the original in parentheses
  And the result follows the pattern: "中文翻译 (Original Term)"
```

### Scenario: Translation API down

```gherkin
Scenario: Translation API completely down
  Given the DeepSeek API returns HTTP 500 or is unreachable
  And there are 20 new items awaiting translation
  When the translation pipeline attempts to process the items
  Then the system retries 3 times with exponential backoff (1s, 3s, 5s)
  And after 3 failures, the system logs an ERROR "Translation API unavailable"
  And items are stored with original_title and original_body in translated fields
  And translated_title is prefixed with "[TRANSLATION_PENDING] "
  And translated_body is the original body text
  And translated_at is set to null
  And the frontend displays a "Translation pending" badge on these items
```

### Scenario: Translation returns malformed JSON

```gherkin
Scenario: Translation returns malformed JSON
  Given the DeepSeek API returns a response that cannot be parsed as JSON
  When the translation pipeline processes the batch
  Then the system retries once with a stricter prompt
  And if the retry succeeds, translations are processed normally
  And if the retry fails, the system falls back to translating items individually
  And individual item translation uses the same system prompt but for a single item
```

### Scenario: Empty body text translation

```gherkin
Scenario: Item with empty or very short body text
  Given an item with original_title "New anime trailer released"
  And original_body is empty or contains fewer than 20 characters
  When the translation pipeline processes this item
  Then the title is translated normally
  And the body is set to the original (possibly empty) text
  And no error is raised for the empty body
```

### Scenario: Translation prompt consistency

```gherkin
Scenario: Batch translation maintains item ordering
  Given a batch of 10 items in a specific order
  When the translation pipeline sends them to DeepSeek V3
  Then the API response contains translations for all 10 items
  And each translation is correctly mapped back to its original item by ID
  And no items are lost or reordered in the process
```

---

## Feature: Heat Score Calculation

### Background

```gherkin
Background:
  Given the heat score formula is:
  """
  score = (source_engagement ^ 0.7) * (1 / (1 + hours_since_fetch / 24))
  For RSS items (no engagement): score = 1.0 * (1 / (1 + hours_since_fetch / 12))
  """
```

### Scenario: Reddit post with upvotes

```gherkin
Scenario: Reddit post with upvotes
  Given a Reddit post with 1234 upvotes fetched 2 hours ago
  When the heat score is calculated
  Then engagement = 1234
  And engagement_factor = 1234 ^ 0.7 = approximately 201.7
  And recency_factor = 1 / (1 + 2/24) = approximately 0.923
  And heat_score = 201.7 * 0.923 = approximately 186.2
```

### Scenario: AniList entry with trending score

```gherkin
Scenario: AniList entry with trending score
  Given an AniList anime entry with trending score 85 fetched 6 hours ago
  When the heat score is calculated
  Then engagement = 85
  And engagement_factor = 85 ^ 0.7 = approximately 30.1
  And recency_factor = 1 / (1 + 6/24) = approximately 0.8
  And heat_score = 30.1 * 0.8 = approximately 24.1
```

### Scenario: Steam game with review count

```gherkin
Scenario: Steam game with review count
  Given a Steam game with 50000 total reviews fetched 1 hour ago
  When the heat score is calculated
  Then engagement = 50000
  And engagement_factor = 50000 ^ 0.7 = approximately 2759.5
  And recency_factor = 1 / (1 + 1/24) = approximately 0.96
  And heat_score = 2759.5 * 0.96 = approximately 2649.1
```

### Scenario: RSS feed item with no engagement data

```gherkin
Scenario: RSS feed item with no engagement data (recency-only scoring)
  Given an RSS item from Anime! Anime! with no engagement data fetched 3 hours ago
  When the heat score is calculated
  Then engagement is not used
  And recency_factor = 1 / (1 + 3/12) = 1 / 1.25 = 0.8
  And heat_score = 0.8
```

### Scenario: Very old item has low heat score

```gherkin
Scenario: Item fetched 48 hours ago has very low heat score
  Given a Reddit post with 500 upvotes fetched 48 hours ago
  When the heat score is calculated
  Then engagement_factor = 500 ^ 0.7 = approximately 102.4
  And recency_factor = 1 / (1 + 48/24) = 1/3 = approximately 0.333
  And heat_score = 102.4 * 0.333 = approximately 34.1
```

### Scenario: Fresh item with high engagement ranks highest

```gherkin
Scenario: Fresh high-engagement item ranks above old high-engagement item
  Given a Reddit post with 500 upvotes fetched 1 hour ago (heat ~474)
  And a Reddit post with 5000 upvotes fetched 48 hours ago (heat ~189)
  When items are sorted by heat_score descending
  Then the fresh 500-upvote post appears before the old 5000-upvote post
```

### Scenario: Zero engagement item

```gherkin
Scenario: Item with zero engagement
  Given a Reddit post with 0 upvotes fetched 1 hour ago
  When the heat score is calculated
  Then engagement = 0
  And engagement_factor = 0 ^ 0.7 = 0
  And heat_score = 0
  And the item appears at the bottom when sorted by heat
```

### Scenario: Heat score recalculated on read

```gherkin
Scenario: Heat score is recalculated at query time
  Given a Reddit post with 1000 upvotes was inserted 12 hours ago
  And the stored heat_score was calculated at insert time (insert-time value)
  When a user requests the feed sorted by heat
  Then the system recalculates the heat_score using current time
  And the recency_factor reflects the actual age of the item
  And items become less hot as they age, even without re-fetching
```

---

## Feature: Feed Display

### Background

```gherkin
Background:
  Given the frontend is a Next.js application using shadcn/ui components
  And the backend API is available at NEXT_PUBLIC_API_URL
```

### Scenario: Display 50 items per page with infinite scroll

```gherkin
Scenario: Display feed items with infinite scroll (happy path)
  Given the database contains 200 feed items
  And the user navigates to the homepage
  When the page loads
  Then the frontend fetches GET /api/feed?sort=hot&page=1&per_page=50
  And the first 50 items are rendered as cards sorted by heat_score descending
  And each card displays: source badge, translated title, translated excerpt, heat score, timestamp
  And each card has a "View original" collapsible link
  And when the user scrolls near the bottom, the next page is fetched
  And page 2 items are appended below page 1
  And loading skeletons are shown during fetch
```

### Scenario: Filter by source

```gherkin
Scenario: Filter feed by source using checkboxes
  Given the top bar displays checkboxes for each source: Reddit, AniList, Steam, Anime News
  And all checkboxes are checked by default (showing all sources)
  When the user unchecks the "Steam" checkbox
  Then the frontend fetches GET /api/feed?sort=hot&sources=reddit,anilist,anime_news
  And only items from Reddit, AniList, and Anime News are displayed
  And Steam items are hidden
  When the user unchecks all checkboxes
  Then the feed shows an empty state: "No items found. Try adjusting your filters."
```

### Scenario: Filter by multiple sources

```gherkin
Scenario: Filter by selecting only Reddit and AniList
  Given the user unchecks "Steam" and "Anime News"
  When only "Reddit" and "AniList" checkboxes are checked
  Then the frontend fetches GET /api/feed?sort=hot&sources=reddit,anilist
  And only items from Reddit and AniList are shown
```

### Scenario: Sort by Hot (heat score)

```gherkin
Scenario: Sort feed by Hot (default)
  Given the top bar has a Hot/New sort toggle
  And "Hot" is selected by default
  When the feed is displayed
  Then items are sorted by heat_score in descending order
  And the highest-scored item appears first
```

### Scenario: Sort by New (fetched_at)

```gherkin
Scenario: Sort feed by New (recency)
  Given the user clicks the "New" sort toggle
  When the frontend fetches GET /api/feed?sort=new&page=1&per_page=50
  Then items are sorted by fetched_at in descending order
  And the most recently fetched item appears first
  And heat scores are still displayed on each card but do not affect order
```

### Scenario: Feed card displays all required fields

```gherkin
Scenario: Feed card displays all required fields
  Given a feed item with:
    | field            | value                                    |
    | source           | reddit                                   |
    | translated_title | "咒术回战第三季制作决定"                |
    | translated_body  | "MAPPA宣布咒术回战第三季动画..."        |
    | heat_score       | 186.2                                    |
    | fetched_at       | 2026-04-09T10:30:00Z                     |
    | source_url       | https://reddit.com/r/anime/comments/abc  |
  When the card is rendered
  Then the card shows a Reddit source badge (colored icon)
  And the translated title is displayed in bold
  And the translated body is displayed as an excerpt (max 3 lines, truncated with ellipsis)
  And the heat score shows "186.2" with a flame icon
  And the timestamp shows relative time (e.g., "2 hours ago")
  And a "View original" link is present, linking to source_url
```

### Scenario: View original link

```gherkin
Scenario: View original link opens source URL
  Given a feed card with source_url "https://reddit.com/r/anime/comments/abc123"
  And the "View original" link is collapsed by default
  When the user clicks to expand the link
  Then the source URL is revealed
  And clicking the URL opens the original Reddit post in a new tab
```

### Scenario: Translation pending badge

```gherkin
Scenario: Card shows translation pending badge when translation failed
  Given a feed item with translated_title starting with "[TRANSLATION_PENDING]"
  When the card is rendered
  Then the card displays a "Translation pending" badge in a muted color
  And the title shows the original text (without the prefix)
  And the body shows the original text
```

### Scenario: Loading state

```gherkin
Scenario: Feed shows loading skeleton while fetching
  Given the user navigates to the homepage
  And the API has not yet responded
  When the page is loading
  Then 10 card-shaped skeletons are displayed
  And each skeleton has animated pulse effect
  And when the API responds, skeletons are replaced with actual cards
```

### Scenario: Mobile responsive layout

```gherkin
Scenario: Feed is responsive on mobile
  Given the user accesses the site on a 375px wide viewport
  When the page loads
  Then the feed cards span full width with appropriate padding
  And source filter checkboxes show as compact icons (not full labels)
  And the sort toggle is accessible in the top bar
  And text wraps appropriately without horizontal scrolling
```

### Scenario: Empty feed

```gherkin
Scenario: Empty feed when database has no items
  Given the database contains 0 feed items
  When the user navigates to the homepage
  Then the feed area shows an empty state component
  And the message reads: "No items yet. The next fetch is coming soon."
  And a loading indicator shows that data is being fetched
```

---

## Feature: Data Retention

### Background

```gherkin
Background:
  Given the APScheduler has a daily cleanup job
  And the retention period is 7 days
```

### Scenario: Auto-cleanup removes items older than 7 days

```gherkin
Scenario: Auto-cleanup removes items older than 7 days
  Given the database contains items from the past 10 days
  And the cleanup job runs daily
  When the cleanup job executes
  Then all items with fetched_at older than 7 days are deleted
  And items from the past 7 days are retained
  And the system logs INFO "Cleaned up N expired items"
```

### Scenario: Cleanup does not affect recent items

```gherkin
Scenario: Cleanup preserves all items from the past 7 days
  Given the database contains 500 items from the past 7 days
  And 200 items older than 7 days
  When the cleanup job executes
  Then the 500 recent items are preserved
  And the 200 old items are deleted
  And the total item count is 500
```

### Scenario: Cleanup runs on schedule

```gherkin
Scenario: Cleanup runs once per day at off-peak hours
  Given the APScheduler has a cleanup job configured
  When the daily schedule triggers (e.g., 04:00 UTC)
  Then the cleanup job executes DELETE FROM feed_items WHERE fetched_at < datetime('now', '-7 days')
  And the job logs the number of deleted items
  And the job updates system_metadata with last_cleanup_at
```

### Scenario: Database size stays within limits

```gherkin
Scenario: Database size stays under 500 MB with retention policy
  Given the system fetches approximately 200 items per day
  And each item averages approximately 1 KB in the database
  And the retention policy is 7 days
  When the system is at steady state
  Then the maximum number of active items is approximately 1400 (200 x 7)
  And the database size is approximately 1.4 MB
  And the database size is well within the 500 MB limit
```

### Scenario: Cleanup handles database errors gracefully

```gherkin
Scenario: Cleanup handles database errors
  Given the SQLite database is temporarily locked or corrupted
  When the cleanup job executes
  Then the DELETE query fails
  And the system logs an ERROR "Cleanup failed: {error details}"
  And the job does not crash the application
  And the next scheduled cleanup will retry
```

---

## Feature: Health Monitoring

### Scenario: Health endpoint reflects system state

```gherkin
Scenario: Health endpoint shows current system state
  Given the system is running normally
  And the last successful fetch was at 2026-04-09T10:30:00Z
  And the database contains 1234 items
  When a client requests GET /api/health
  Then the response is:
    | field          | value                    |
    | status         | "healthy"                |
    | last_fetch_at  | "2026-04-09T10:30:00Z"  |
    | total_items    | 1234                     |
    | db_size_mb     | 12.5                     |
```

### Scenario: Health endpoint shows degraded state

```gherkin
Scenario: Health endpoint shows degraded state after failed fetch
  Given the last 3 fetch cycles all failed
  And the last successful fetch was 2 hours ago
  When a client requests GET /api/health
  Then the response status is "degraded"
  And last_fetch_at reflects the last successful fetch time
  And an additional field last_fetch_status is "all_sources_failed"
```

### Scenario: Sources endpoint lists available sources

```gherkin
Scenario: Sources endpoint returns source configuration
  When a client requests GET /api/sources
  Then the response includes:
    | name        | label           | enabled |
    | reddit      | Reddit          | true    |
    | anilist     | AniList         | true    |
    | steam       | Steam           | true    |
    | anime_news  | Anime News (JP) | true    |
```

---

## Feature: Admin Trigger Endpoint

### Scenario: Admin triggers manual fetch successfully

```gherkin
Scenario: Admin triggers manual fetch successfully
  Given the backend is running
  When a POST request is sent to /api/admin/trigger-fetch with valid X-Admin-Key header
  Then the response status is 200
  And the response contains "status": "fetch_triggered"
  And a fetch cycle begins immediately
```

### Scenario: Admin endpoint rejects invalid key

```gherkin
Scenario: Admin endpoint rejects invalid key
  Given the backend is running
  When a POST request is sent to /api/admin/trigger-fetch with an invalid X-Admin-Key header
  Then the response status is 401
  And the response contains "detail": "Unauthorized"
  And no fetch cycle is triggered
```

### Scenario: Admin endpoint rejects missing key

```gherkin
Scenario: Admin endpoint rejects missing key
  Given the backend is running
  When a POST request is sent to /api/admin/trigger-fetch without X-Admin-Key header
  Then the response status is 401
```

---

## Feature: TabBar Placeholder Tabs

### Scenario: TabBar shows Feed tab as active

```gherkin
Scenario: TabBar shows Feed tab as active
  When the user views the feed page
  Then the "Feed" tab is displayed and visually active
  And the "Social" tab is displayed but disabled (grayed out)
  And the "Search" tab is displayed but disabled (grayed out)
```

### Scenario: Disabled tabs show coming soon tooltip

```gherkin
Scenario: Disabled tabs show coming soon tooltip
  When the user hovers over (desktop) or taps (mobile) the "Social" tab
  Then a tooltip or label shows "Coming soon"
  And no navigation occurs
```

---

## Feature: Body Truncation

### Scenario: Long body text is truncated to 500 characters

```gherkin
Scenario: Long body text is truncated to 500 characters
  Given Reddit returns a post with selftext of 1500 characters
  When the fetcher processes this item
  Then original_body is stored as the first 500 characters of the selftext
  And the translation pipeline translates only the truncated body
```

### Scenario: Short body text is stored as-is

```gherkin
Scenario: Short body text is stored as-is
  Given AniList returns a media item with description of 200 characters
  When the fetcher processes this item
  Then original_body is stored as the full 200-character description
```

---

## Feature: Startup Catch-Up

### Scenario: Backend triggers fetch on startup after missed cycle

```gherkin
Scenario: Backend triggers fetch on startup after missed cycle
  Given the backend has been restarted
  And system_metadata.last_fetch_at is 45 minutes ago
  When the backend finishes startup
  Then an immediate fetch cycle is triggered
  And new items are fetched, translated, and stored
```

### Scenario: Backend skips startup fetch when recently fetched

```gherkin
Scenario: Backend skips startup fetch when recently fetched
  Given the backend has been restarted
  And system_metadata.last_fetch_at is 10 minutes ago
  When the backend finishes startup
  Then no immediate fetch cycle is triggered
  And the next scheduled fetch runs at its normal time
```
