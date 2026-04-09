# Task 008: Frontend Project Setup

**depends-on**: (none)

## Description

Scaffold the Next.js frontend project with App Router, shadcn/ui, Tailwind CSS, and core configuration. This creates the foundation for the feed display components.

## Execution Context

**Task Number**: 008 of 009
**Phase**: Setup
**Prerequisites**: Node.js 18+ installed

## BDD Scenario

No specific BDD scenario — this is project scaffolding.

## Files to Modify/Create

- Create: `frontend/` directory (Next.js app)
- Create: `frontend/package.json` (next, react, tailwindcss, shadcn/ui deps)
- Create: `frontend/app/layout.tsx` (root layout)
- Create: `frontend/app/page.tsx` (home page placeholder)
- Create: `frontend/lib/api.ts` (API client)
- Create: `frontend/lib/types.ts` (TypeScript interfaces)
- Create: `frontend/lib/constants.ts` (source config)
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/next.config.js`

## Steps

### Step 1: Create Next.js project
- Run `npx create-next-app@latest frontend --typescript --tailwind --app --src-dir=false --import-alias="@/*"`
- Or manually create the project structure

### Step 2: Install and configure shadcn/ui
- Run `npx shadcn@latest init` with defaults
- Install needed components: `npx shadcn@latest add card badge checkbox skeleton toggle button tooltip`

### Step 3: Create TypeScript types
- Create `lib/types.ts` matching backend Pydantic models:
  - `FeedItem`: id, source, sourceUrl, translatedTitle, translatedBody, heatScore, sourceMetadata, fetchedAt, translatedAt, language
  - `FeedResponse`: items, total, page, perPage, hasNext
  - `SourceConfig`: name, label, enabled
  - `HealthResponse`: status, lastFetchAt, totalItems, dbSizeMb
  - `SortOption`: "hot" | "new"
  - `SourceName`: "reddit" | "anilist" | "steam" | "anime_news"

### Step 4: Create API client
- Create `lib/api.ts`:
  - `getFeed(params: {sort?, sources?, page?, per_page?}): Promise<FeedResponse>`
  - `getFeedItem(id: string): Promise<FeedItem>`
  - `getSources(): Promise<SourceConfig[]>`
  - `getHealth(): Promise<HealthResponse>`
  - Base URL from `NEXT_PUBLIC_API_URL` env var

### Step 5: Create constants
- Create `lib/constants.ts`:
  - `SOURCE_CONFIG`: Map of source names to {label, color, icon}
  - `DEFAULT_PAGE_SIZE`: 20
  - `MAX_PAGE_SIZE`: 50

### Step 6: Verify setup
- Run `npm run dev` — should start without errors
- Visit `http://localhost:3000` — should render placeholder page

## Verification Commands

```bash
cd frontend
npm install
npm run dev  # Should start
npm run build  # Should build without errors
```

## Success Criteria

- Next.js app starts without errors
- shadcn/ui components available
- TypeScript types match backend models
- API client configured with correct base URL
