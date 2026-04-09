# Task 009: Feed Display Components Impl

**depends-on**: task-009-feed-display-test, task-007-api-endpoints-impl

## Description

Implement all frontend components: FeedCard, FeedList, TopBar, TabBar, LoadingSkeleton, EmptyState, and ViewOriginal using shadcn/ui and Tailwind CSS with responsive mobile-first design.

## Execution Context

**Task Number**: 009 of 009
**Phase**: Core Features
**Prerequisites**: Frontend tests exist (task-009-test), API endpoints working (task-007-impl)

## BDD Scenario

Same scenarios as task-009-test — implementation makes them pass.

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `frontend/components/feed/FeedCard.tsx`
- Create: `frontend/components/feed/FeedList.tsx`
- Create: `frontend/components/feed/SourceBadge.tsx`
- Create: `frontend/components/feed/HeatScore.tsx`
- Create: `frontend/components/feed/ViewOriginal.tsx`
- Create: `frontend/components/feed/LoadingSkeleton.tsx`
- Create: `frontend/components/feed/EmptyState.tsx`
- Create: `frontend/components/layout/TopBar.tsx`
- Create: `frontend/components/layout/TabBar.tsx`
- Modify: `frontend/app/page.tsx` (wire up all components)
- Modify: `frontend/app/layout.tsx` (global styles, metadata)

## Steps

### Step 1: Implement FeedCard
- Props: `item: FeedItem`
- Renders: SourceBadge (top-right), translated title (bold), translated body (3-line clamp), HeatScore + relative time, ViewOriginal (collapsible)
- If title starts with [TRANSLATION_PENDING], show TranslationPendingBadge
- Responsive: full-width on mobile, max-w-2xl on desktop

### Step 2: Implement SourceBadge
- Props: `source: SourceName`
- Colored badge using shadcn Badge component
- Colors: Reddit=orange, AniList=blue, Steam=gray, Anime News=purple

### Step 3: Implement HeatScore
- Props: `score: number`
- Display score with flame icon (lucide-react)

### Step 4: Implement ViewOriginal
- Props: `url: string`
- Collapsed by default, click to expand
- Opens in new tab with rel="noopener noreferrer"

### Step 5: Implement TopBar
- Props: `activeSources, onSourcesChange, activeSort, onSortChange`
- Logo left, source checkboxes center, hot/new toggle right
- On mobile: checkboxes collapse to compact icons

### Step 6: Implement TabBar
- Three tabs: Feed (active), Social (disabled), Search (disabled)
- Tooltip "Coming soon" on disabled tabs using shadcn Tooltip

### Step 7: Implement FeedList
- Fetches from API using `getFeed()`
- Renders list of FeedCard components
- Infinite scroll using Intersection Observer
- Shows LoadingSkeleton during fetch
- Shows EmptyState when no items match filters
- Passes filter/sort state from TopBar to API

### Step 8: Wire up page.tsx
- Import and compose TopBar, TabBar, FeedList
- Manage state for active sources, sort option
- Pass state changes down to FeedList for re-fetching

### Step 9: Verify tests pass (Green)
- Run `npm test`

## Verification Commands

```bash
cd frontend
npm test -- --run  # All should PASS
npm run build  # Should build without errors
npm run dev  # Visual check: responsive, all components render
```

## Success Criteria

- All frontend component tests pass
- Feed displays cards with all required fields
- Source filtering and hot/new sorting work
- Infinite scroll pagination works
- Mobile responsive (320px-428px)
- TabBar with disabled placeholder tabs
- Loading skeletons and empty state
