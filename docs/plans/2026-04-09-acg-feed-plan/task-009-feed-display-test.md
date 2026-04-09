# Task 009: Feed Display Components Test

**depends-on**: task-008

## Description

Write failing tests for the frontend feed display components: FeedCard, FeedList, TopBar, TabBar, and related UI elements. Tests use React Testing Library with mocked API responses.

## Execution Context

**Task Number**: 009 of 009
**Phase**: Core Features
**Prerequisites**: Frontend project setup exists (task-008)

## BDD Scenario

```gherkin
Scenario: Feed card displays all required fields
  Given a feed item with translated_title "咒术回战第三季制作决定"
  When the card is rendered
  Then the card shows a Reddit source badge
  And the translated title is displayed in bold
  And the translated body is displayed as an excerpt
  And the heat score shows with flame icon
  And the timestamp shows relative time

Scenario: View original link opens source URL
  Given a feed card with source_url
  And the "View original" link is collapsed by default
  When the user clicks to expand
  Then the source URL is revealed

Scenario: Card shows translation pending badge
  Given a feed item with translated_title starting with "[TRANSLATION_PENDING]"
  When the card is rendered
  Then a "Translation pending" badge is displayed

Scenario: Feed shows loading skeleton while fetching
  Given the API has not yet responded
  When the page is loading
  Then card-shaped skeletons are displayed

Scenario: TabBar shows Feed tab as active
  When the user views the feed page
  Then "Feed" tab is active, "Social" and "Search" are disabled

Scenario: Disabled tabs show coming soon tooltip
  When the user hovers over "Social" tab
  Then "Coming soon" tooltip appears

Scenario: Empty feed
  Given the database contains 0 items
  When the user navigates to the homepage
  Then "No items yet" message is shown

Scenario: Filter feed by source using checkboxes
  When the user unchecks "Steam"
  Then only Reddit, AniList, Anime News items shown

Scenario: Sort feed by Hot (default)
  Then items are sorted by heat_score descending

Scenario: Sort feed by New
  When user clicks "New" sort
  Then items are sorted by fetched_at descending
```

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `frontend/__tests__/FeedCard.test.tsx`
- Create: `frontend/__tests__/FeedList.test.tsx`
- Create: `frontend/__tests__/TopBar.test.tsx`
- Create: `frontend/__tests__/TabBar.test.tsx`

## Steps

### Step 1: Install test dependencies
- Install: `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `vitest`, `jsdom`

### Step 2: Write FeedCard tests
- `test_renders_all_fields`: Verify source badge, title, body, heat score, timestamp
- `test_translation_pending_badge`: Verify badge appears for [TRANSLATION_PENDING] items
- `test_view_original_collapsed`: Verify link collapsed by default, expands on click

### Step 3: Write FeedList tests
- `test_shows_loading_skeleton`: Verify skeletons while loading
- `test_shows_empty_state`: Verify empty message when no items
- `test_pagination_infinite_scroll`: Verify next page fetched on scroll

### Step 4: Write TopBar tests
- `test_source_filter_checkboxes`: Verify filtering by source
- `test_sort_toggle_hot_new`: Verify sort switching

### Step 5: Write TabBar tests
- `test_feed_tab_active`: Verify Feed tab is active by default
- `test_disabled_tabs_tooltip`: Verify "Coming soon" on disabled tabs

### Step 6: Verify tests fail (Red)

## Verification Commands

```bash
cd frontend
npm test -- --run  # All should FAIL
```

## Success Criteria

- All frontend component tests exist and fail
- Tests mock API calls (no real backend)
- Tests cover card rendering, loading states, filtering, sorting, TabBar
