# ACG Feed Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Load `superpowers:executing-plans` skill using the Skill tool to implement this plan task-by-task.

**Goal:** Build an AI-translated ACG news feed aggregator that pulls from Reddit, AniList, Steam, and Japanese RSS feeds, translates to Chinese via DeepSeek V3, and displays in a heat-ranked single-page feed.

**Architecture:** FastAPI backend with APScheduler cron (every 30 min) fetches → translates → scores → stores in SQLite. Next.js App Router frontend with shadcn/ui renders server-side paginated feed. Deployed on Vercel (frontend) + Railway (backend).

**Tech Stack:** Python 3.12+, FastAPI, APScheduler, httpx, aiosqlite, DeepSeek V3 API, Next.js 14+, shadcn/ui, Tailwind CSS, Vercel, Railway

**Design Support:**
- [BDD Specs](../2026-04-09-acg-feed-design/bdd-specs.md)
- [Architecture](../2026-04-09-acg-feed-design/architecture.md)
- [Best Practices](../2026-04-09-acg-feed-design/best-practices.md)
- [Design Index](../2026-04-09-acg-feed-design/_index.md)

## Context

This is greenfield development for an MVP targeting Chinese-speaking ACG fans. The founder is the primary user, spending 2+ hours daily across scattered platforms. Translation IS the product — removing language barriers to the richest global ACG content. No accounts, no social, no tracking. Pure content consumption to validate the thesis: "If you build a translated feed, will people come back on day 3 and day 7?"

**Constraints:** Solo engineer, 3-5 day build target, under $20/day translation cost, mobile-first responsive web.

## Execution Plan

```yaml
tasks:
  - id: "001"
    subject: "Backend project setup"
    slug: "backend-project-setup"
    type: "setup"
    depends-on: []
  - id: "002"
    subject: "Database layer"
    slug: "database-impl"
    type: "impl"
    depends-on: ["001"]
  - id: "003"
    subject: "Heat score calculation test"
    slug: "heat-score-test"
    type: "test"
    depends-on: ["001"]
  - id: "003"
    subject: "Heat score calculation impl"
    slug: "heat-score-impl"
    type: "impl"
    depends-on: ["003-test"]
  - id: "004"
    subject: "Source fetchers test"
    slug: "source-fetchers-test"
    type: "test"
    depends-on: ["001"]
  - id: "004"
    subject: "Source fetchers impl"
    slug: "source-fetchers-impl"
    type: "impl"
    depends-on: ["004-test"]
  - id: "005"
    subject: "Translation service test"
    slug: "translation-service-test"
    type: "test"
    depends-on: ["001"]
  - id: "005"
    subject: "Translation service impl"
    slug: "translation-service-impl"
    type: "impl"
    depends-on: ["005-test"]
  - id: "006"
    subject: "Fetch orchestrator & cron test"
    slug: "orchestrator-test"
    type: "test"
    depends-on: ["002", "003-impl", "004-impl", "005-impl"]
  - id: "006"
    subject: "Fetch orchestrator & cron impl"
    slug: "orchestrator-impl"
    type: "impl"
    depends-on: ["006-test"]
  - id: "007"
    subject: "API endpoints test"
    slug: "api-endpoints-test"
    type: "test"
    depends-on: ["002"]
  - id: "007"
    subject: "API endpoints impl"
    slug: "api-endpoints-impl"
    type: "impl"
    depends-on: ["007-test"]
  - id: "008"
    subject: "Frontend project setup"
    slug: "frontend-setup"
    type: "setup"
    depends-on: []
  - id: "009"
    subject: "Feed display components test"
    slug: "feed-display-test"
    type: "test"
    depends-on: ["008"]
  - id: "009"
    subject: "Feed display components impl"
    slug: "feed-display-impl"
    type: "impl"
    depends-on: ["009-test", "007-impl"]
```

**Task File References (for detailed BDD scenarios):**
- [Task 001: Backend project setup](./task-001-backend-project-setup.md)
- [Task 002: Database layer](./task-002-database-impl.md)
- [Task 003: Heat score calculation test](./task-003-heat-score-test.md)
- [Task 003: Heat score calculation impl](./task-003-heat-score-impl.md)
- [Task 004: Source fetchers test](./task-004-source-fetchers-test.md)
- [Task 004: Source fetchers impl](./task-004-source-fetchers-impl.md)
- [Task 005: Translation service test](./task-005-translation-service-test.md)
- [Task 005: Translation service impl](./task-005-translation-service-impl.md)
- [Task 006: Fetch orchestrator & cron test](./task-006-orchestrator-test.md)
- [Task 006: Fetch orchestrator & cron impl](./task-006-orchestrator-impl.md)
- [Task 007: API endpoints test](./task-007-api-endpoints-test.md)
- [Task 007: API endpoints impl](./task-007-api-endpoints-impl.md)
- [Task 008: Frontend project setup](./task-008-frontend-setup.md)
- [Task 009: Feed display components test](./task-009-feed-display-test.md)
- [Task 009: Feed display components impl](./task-009-feed-display-impl.md)

## BDD Coverage

All BDD scenarios from `bdd-specs.md` are covered by these tasks:

| Feature | Scenarios | Covered By Task |
|---------|-----------|-----------------|
| Feed Aggregation (7) | Happy path, Reddit down, AniList down, Duplicate detection, All sources fail, Partial failure, Fetch timing | 004 (fetchers), 006 (orchestrator) |
| Translation (8) | Happy path, Rate limited, ACG terminology, Unknown terminology, API down, Malformed JSON, Empty body, Batch ordering | 005 |
| Heat Score (8) | Reddit upvotes, AniList trending, Steam reviews, RSS recency, Old decay, Fresh vs old, Zero engagement, Recalculate on read | 003 |
| Feed Display (11) | Infinite scroll, Source filter, Multi-source, Sort Hot, Sort New, Card fields, View original, Translation pending, Loading, Mobile, Empty | 007 (API), 009 (UI) |
| Data Retention (5) | Auto-cleanup, Preserve recent, Scheduled cleanup, DB size, DB errors | 002, 006 |
| Health Monitoring (3) | Healthy, Degraded, Sources list | 007 |
| Admin Trigger (3) | Success, Invalid key, Missing key | 007 |
| TabBar (2) | Feed active, Coming soon tooltip | 009 |
| Body Truncation (2) | Long body, Short body | 004 |
| Startup Catch-Up (2) | Missed cycle, Recently fetched | 006 |

## Dependency Chain

```
001 (backend setup)
├── 002 (database)
│   ├── 006-test (orchestrator) ◄── also needs 003-impl, 004-impl, 005-impl
│   │   └── 006-impl
│   └── 007-test (API endpoints)
│       └── 007-impl ─────────────────────────┐
│                                              │
├── 003-test (heat score)                      │
│   └── 003-impl ──┐                           │
│                  ├──► 006-test               │
├── 004-test (fetchers)                        │
│   └── 004-impl ──┤                           │
│                  │                           │
├── 005-test (translation)                     │
│   └── 005-impl ──┘                           │
│                                              │
008 (frontend setup)                           │
└── 009-test (feed display)                    │
    └── 009-impl ◄─────────────────────────────┘
```

**Analysis**:
- No circular dependencies
- Backend (001-007) and frontend (008-009) can start in parallel
- Tasks 002-005 can proceed in parallel after 001 setup
- Task 006 (orchestrator) is the convergence point for all backend components
- Task 009-impl depends on both frontend setup (008) and API endpoints (007-impl)

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-04-09-acg-feed-plan/`. Execution options:

**1. Orchestrated Execution (Recommended)** - Load `superpowers:executing-plans` skill using the Skill tool.

**2. Direct Agent Team** - Load `superpowers:agent-team-driven-development` skill using the Skill Tool.

**3. BDD-Focused Execution** - Load `superpowers:behavior-driven-development` skill using the Skill Tool for specific scenarios.
