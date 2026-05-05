---
name: openclaw-acghacknews-reddit-to-hacknews
description: Read the ACG Hack News API doc, visit the Reddit recommended sections, pick Reddit posts that are worth adding to Hack News, then submit them to the admin API at https://api2.reelbit.cc using an apikey. Use when the task is to curate Reddit ACG posts and add them into Hack News.
metadata:
  openclaw:
    homepage: https://api2.reelbit.cc
---

# OpenClaw Skill: Reddit -> Hack News

## Language

Match the user's language. If the user writes in Chinese, respond in Chinese. If the user writes in English, respond in English.

## Goal

This skill is for manually curating Reddit ACG-related posts and inserting selected items into Hack News through the admin API.

Source of truth for the API contract:

# ACG Feed API 文档

Base URL: `https://api2.reelbit.cc`

## 认证

管理接口需要在请求头中携带 `X-Admin-Key`，值为 `.env` 中配置的 `ADMIN_API_KEY`。

```
X-Admin-Key: qyquyue19
```

---

## 公开接口

### GET /api/feed

获取信息流列表，支持分页、排序和来源筛选。

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `per_page` | int | 20 | 每页数量 (1-50) |
| `sort` | string | "hot" | 排序方式：`hot`（热度降序）、`new`（时间降序） |
| `sources` | string | - | 来源筛选，逗号分隔。可选值：`reddit`, `anilist`, `steam`, `anime_news` |

**示例：**

```bash
# 获取热门信息流
curl https://api2.reelbit.cc/api/feed

# 只看 Reddit 和 Steam，按最新排序
curl "https://api2.reelbit.cc/api/feed?sources=reddit,steam&sort=new"

# 第2页
curl "https://api2.reelbit.cc/api/feed?page=2&per_page=10"
```

**响应：**

```json
{
  "items": [
    {
      "id": "abc123",
      "source": "reddit",
      "source_url": "https://reddit.com/r/anime/comments/xxx",
      "original_title": "Original Title",
      "translated_title": "中文标题",
      "original_body": "原文内容...",
      "translated_body": "翻译内容...",
      "heat_score": 85.5,
      "source_metadata": {"subreddit": "anime", "score": 500},
      "language": "zh-CN",
      "fetched_at": "2026-04-17T10:00:00+00:00",
      "translated_at": "2026-04-17T10:00:05+00:00"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "has_next": true
}
```

### GET /api/feed/{item_id}

获取单条信息详情。

**示例：**

```bash
curl https://api2.reelbit.cc/api/feed/abc123
```

**响应：** 单个 FeedItem 对象（同上 items 中的元素格式）。

### GET /api/health

健康检查，返回系统状态。

```bash
curl https://api2.reelbit.cc/api/health
```

**响应：**

```json
{
  "status": "ok",
  "last_fetch_at": "2026-04-17T10:00:00+00:00",
  "total_items": 150,
  "db_size_mb": 1.23,
  "last_fetch_status": "success"
}
```

### GET /api/sources

获取所有数据源配置。

```bash
curl https://api2.reelbit.cc/api/sources
```

**响应：**

```json
{
  "sources": [
    {"name": "reddit", "label": "Reddit", "enabled": true},
    {"name": "anilist", "label": "AniList", "enabled": true},
    {"name": "steam", "label": "Steam", "enabled": true},
    {"name": "anime_news", "label": "Anime News", "enabled": true}
  ]
}
```

---

## 管理接口

以下接口需要 `X-Admin-Key` 认证。

### POST /api/admin/trigger-fetch

手动触发一次全量抓取（所有数据源）。

```bash
curl -X POST https://api2.reelbit.cc/api/admin/trigger-fetch \
  -H "X-Admin-Key: your-admin-api-key"
```

**响应：**

```json
{"status": "fetch_triggered"}
```

### POST /api/admin/items

手动插入数据条目，支持批量插入。`source_url` 用于去重，重复 URL 会被静默跳过。`id` 和 `fetched_at` 自动生成。

**请求体：**

```json
{
  "items": [
    {
      "source": "reddit",
      "source_url": "https://reddit.com/r/anime/comments/xxx",
      "original_title": "英文标题",
      "translated_title": "中文翻译标题",
      "original_body": "原文内容（可选）",
      "translated_body": "翻译内容（可选）",
      "heat_score": 75.0,
      "source_metadata": {"subreddit": "anime", "score": 500},
      "language": "zh-CN"
    }
  ]
}
```

**字段说明：**

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `source` | 是 | string | 来源：`reddit` / `anilist` / `steam` / `anime_news` |
| `source_url` | 是 | string | 原文链接，用于去重 |
| `original_title` | 是 | string | 原始标题 |
| `translated_title` | 是 | string | 翻译后标题 |
| `original_body` | 否 | string | 原始正文，默认空 |
| `translated_body` | 否 | string | 翻译后正文，默认空 |
| `heat_score` | 否 | float | 热度分数，默认 0.0 |
| `source_metadata` | 否 | object | 来源元数据，默认 `{}` |
| `language` | 否 | string | 语言代码，默认 `zh-CN` |

**示例：**

```bash
curl -X POST https://api2.reelbit.cc/api/admin/items \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-api-key" \
  -d '{
    "items": [
      {
        "source": "reddit",
        "source_url": "https://reddit.com/r/anime/comments/abc123",
        "original_title": "New Anime Announcement",
        "translated_title": "新动画企划发表",
        "original_body": "A new anime has been announced...",
        "translated_body": "一部新动画已宣布...",
        "heat_score": 80.0,
        "source_metadata": {"subreddit": "anime", "score": 500, "num_comments": 120}
      },
      {
        "source": "steam",
        "source_url": "https://store.steampowered.com/app/12345",
        "original_title": "Game Release",
        "translated_title": "游戏发售",
        "heat_score": 60.0
      }
    ]
  }'
```

**响应：**

```json
{"status": "ok", "inserted": 2, "total": 2}
```

- `inserted` — 实际插入数量（去重后）
- `total` — 提交总数

---

## 数据源参考

### Reddit 推荐板块

后端通过 Reddit OAuth2 API 抓取各板块的 hot 帖子，当前已配置的板块见 `app/fetchers/reddit.py` 中的 `SUPPORTED_SUBREDDITS`。

以下是 ACG 领域推荐的板块（按活跃度排序），可用于手动抓取或扩展配置：

#### 动画

| 板块 | 链接 | 成员数 | 说明 |
|------|------|--------|------|
| r/anime | https://www.reddit.com/r/anime/ | ~8M | 最大的英文动画社区，每季新番讨论、新闻、评分 |
| r/animesuggest | https://www.reddit.com/r/animesuggest/ | ~400K | 动画推荐社区，适合发现冷门佳作 |
| r/Animemes | https://www.reddit.com/r/Animemes/ | ~3M | 动画梗图社区，高活跃度 |
| r/TrueAnime | https://www.reddit.com/r/TrueAnime/ | ~200K | 深度动画讨论和分析 |
| r/Donghua  | https://www.reddit.com/r/Donghua/ | ~100K | 中国动画讨论，新连载推荐 |

#### 漫画 / 轻小说

| 板块 | 链接 | 成员数 | 说明 |
|------|------|--------|------|
| r/manga | https://www.reddit.com/r/manga/ | ~4M | 漫画讨论、新连载推荐 |
| r/lightnovels | https://www.reddit.com/r/lightnovels/ | ~600K | 轻小说讨论，动画化新闻第一手来源 |
| r/mangasuggest | https://www.reddit.com/r/mangasuggest/ | ~200K | 漫画推荐 |

#### 游戏（ACG 向）

| 板块 | 链接 | 成员数 | 说明 |
|------|------|--------|------|
| r/gaming | https://www.reddit.com/r/gaming/ | ~40M | 最大游戏社区，含大量 ACG 游戏内容 |
| r/Games | https://www.reddit.com/r/Games/ | ~4M | 游戏新闻和讨论，内容质量较高 |
| r/JRPG | https://www.reddit.com/r/JRPG/ | ~500K | 日式 RPG 专版，原神/FF/DQ 等 |
| r/gachagaming | https://www.reddit.com/r/gachagaming/ | ~400K | 抽卡手游社区（原神、崩坏、FGO 等） |
| r/visualnovels | https://www.reddit.com/r/visualnovels/ | ~300K | Galgame / 视觉小说社区 |

#### ACG 综合社区

| 板块 | 链接 | 成员数 | 说明 |
|------|------|--------|------|
| r/Animesauce | https://www.reddit.com/r/Animesauce/ | ~100K | 动画来源查找 |
| r/MyAnimeList | https://www.reddit.com/r/MyAnimeList/ | ~200K | MAL 社区讨论 |
| r/VNDB | https://www.reddit.com/r/vndb/ | ~10K | 视觉小说数据库社区 |

#### 手动插入示例

用 `POST /api/admin/items` 抓取特定 Reddit 帖子后插入：

```bash
# 假设从 r/JRPG 抓到了一条帖子
curl -X POST https://api2.reelbit.cc/api/admin/items \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: your-admin-api-key" \
  -d '{
    "items": [{
      "source": "reddit",
      "source_url": "https://www.reddit.com/r/JRPG/comments/xxx",
      "original_title": "New Dragon Quest XII details announced",
      "translated_title": "《勇者斗恶龙XII》新情报公开",
      "original_body": "Square Enix revealed new details...",
      "translated_body": "Square Enix 公布了新细节...",
      "heat_score": 90.0,
      "source_metadata": {"subreddit": "JRPG", "ups": 1200, "num_comments": 340}
    }]
  }'
```


Target API base URL for this skill:

- `https://api2.reelbit.cc`

Authentication header:

- `X-Admin-Key: <apikey>`

## When To Use

Use this skill when the task mentions any of the following:

- 从 Reddit 推荐板块里挑选内容并添加到 Hack News
- 根据 `docs/API.md` 手动导入 Reddit 帖子
- 使用 `https://api2.reelbit.cc` 和 `apikey` 添加 ACG 新闻
- Curate Reddit ACG posts and submit them into Hack News

## Required Inputs

Collect or confirm these inputs before submission:

- `apikey`: used as `X-Admin-Key`
- one or more target subreddits from the Reddit recommended sections in [docs/API.md](/Users/quyue/www/acghacknews/docs/API.md)
- one or more Reddit post URLs or raw post data

If the user does not specify subreddits, start from these defaults because they align with the current backend fetcher and the doc's recommendation set:

- `r/anime`
- `r/manga`
- `r/Games`

Expand only when the task calls for broader discovery. Good next choices:

- `r/JRPG`
- `r/gachagaming`
- `r/lightnovels`
- `r/visualnovels`
- `r/animesuggest`

## Selection Rules

Only add posts that are plausibly useful as Hack News items. Prefer:

- new announcements, release dates, trailers, key visual reveals
- patch notes, launch news, platform release news
- industry or creator news with clear ACG relevance
- discussion posts with unusually high engagement and concrete information value

Skip or de-prioritize:

- low-effort memes, shitposts, reaction bait
- recommendation requests without durable news value
- duplicate links or reposted discussion of the same event
- posts with vague titles and no extractable information

Use lightweight filtering heuristics:

- prefer posts with meaningful title information
- prefer posts with substantial body text or linked context
- prefer posts with stronger engagement, such as higher upvotes and comment count
- prefer recent posts over stale threads when multiple posts cover the same topic

## Deduplication Rules

The backend deduplicates by `source_url`. Before submitting, avoid obvious duplicates:

1. If you already have the exact same Reddit permalink in the current batch, keep only one.
2. If the same news event appears in multiple Reddit threads, keep the clearest and most informative one.
3. If a thread is only repeating an older announcement, skip it unless it adds materially new facts.

## Submission Schema

Submit to:

- `POST https://api2.reelbit.cc/api/admin/items`

Headers:

```http
Content-Type: application/json
X-Admin-Key: <apikey>
```

Request body shape:

```json
{
  "items": [
    {
      "source": "reddit",
      "source_url": "https://www.reddit.com/r/anime/comments/xxx",
      "original_title": "Original title",
      "translated_title": "中文标题",
      "original_body": "Original body text",
      "translated_body": "中文正文",
      "heat_score": 80.0,
      "source_metadata": {
        "subreddit": "anime",
        "ups": 1200,
        "num_comments": 340
      },
      "language": "zh-CN"
    }
  ]
}
```

## Field Mapping

Map Reddit data into the API payload like this:

- `source`: always `"reddit"`
- `source_url`: canonical Reddit permalink, prefer `https://www.reddit.com/...`
- `original_title`: Reddit post title
- `translated_title`: translate the title into Chinese unless the user explicitly wants another target language
- `original_body`: use the post selftext if present; otherwise use empty string
- `translated_body`: translate `original_body` into Chinese if there is meaningful content; otherwise use empty string
- `heat_score`: derive from engagement; use a reasonable numeric score rather than inventing fake precision
- `source_metadata.subreddit`: subreddit name without `r/`
- `source_metadata.ups`: Reddit upvote count if known
- `source_metadata.num_comments`: Reddit comment count if known
- `source_metadata.permalink`: include when available
- `source_metadata.author`: include when available
- `language`: default to `zh-CN`

## Heat Score Guidance

The API accepts a float. Use a simple, consistent heuristic. Do not overfit.

Recommended scoring bands:

- `90-100`: major announcement or extremely high-engagement thread
- `75-89`: clearly valuable and hot within its subreddit
- `60-74`: useful but less significant
- `0-59`: usually not worth submitting unless the user explicitly wants broad coverage

Use engagement and news value together. A meme with high upvotes should still be skipped.

## Workflow

1. Read [docs/API.md](/Users/quyue/www/acghacknews/docs/API.md), especially:
   - `POST /api/admin/items`
   - `### Reddit 推荐板块`
2. Choose target subreddit candidates from the recommended Reddit sections.
3. Visit or inspect the candidate Reddit posts.
4. Filter posts using the selection rules above.
5. For each selected post, prepare one item object with translated Chinese fields.
6. Submit the batch to `https://api2.reelbit.cc/api/admin/items` with `X-Admin-Key`.
7. Report the result:
   - how many candidate posts were reviewed
   - how many were submitted
   - how many were inserted according to the API response
   - which posts were skipped and why, if relevant

## Curl Template

Use this request format when performing the final insertion:

```bash
curl -X POST https://api2.reelbit.cc/api/admin/items \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: <apikey>" \
  -d '{
    "items": [
      {
        "source": "reddit",
        "source_url": "https://www.reddit.com/r/JRPG/comments/xxx",
        "original_title": "New Dragon Quest XII details announced",
        "translated_title": "《勇者斗恶龙XII》新情报公开",
        "original_body": "Square Enix revealed new details...",
        "translated_body": "Square Enix 公布了新细节...",
        "heat_score": 90.0,
        "source_metadata": {
          "subreddit": "JRPG",
          "ups": 1200,
          "num_comments": 340
        },
        "language": "zh-CN"
      }
    ]
  }'
```

## Output Expectations

When using this skill, the agent should provide:

- the shortlist of Reddit posts considered
- the final items selected for submission
- the exact submission summary from the API response

If the agent cannot access Reddit content directly, it should ask for the post URLs or raw post data instead of inventing missing fields.
