# ACG Feed API 文档

Base URL: `http://localhost:8000`

## 认证

管理接口需要在请求头中携带 `X-Admin-Key`，值为 `.env` 中配置的 `ADMIN_API_KEY`。

```
X-Admin-Key: your-admin-api-key
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
curl http://localhost:8000/api/feed

# 只看 Reddit 和 Steam，按最新排序
curl "http://localhost:8000/api/feed?sources=reddit,steam&sort=new"

# 第2页
curl "http://localhost:8000/api/feed?page=2&per_page=10"
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
curl http://localhost:8000/api/feed/abc123
```

**响应：** 单个 FeedItem 对象（同上 items 中的元素格式）。

### GET /api/health

健康检查，返回系统状态。

```bash
curl http://localhost:8000/api/health
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
curl http://localhost:8000/api/sources
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
curl -X POST http://localhost:8000/api/admin/trigger-fetch \
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
curl -X POST http://localhost:8000/api/admin/items \
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
curl -X POST http://localhost:8000/api/admin/items \
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
