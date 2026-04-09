import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FeedCard } from '../components/feed/FeedCard'
import type { FeedItem } from '../lib/types'

const mockFeedItem: FeedItem = {
  id: 'test-1',
  source: 'reddit',
  source_url: 'https://reddit.com/r/anime/test',
  translated_title: 'Best Anime of 2024',
  translated_body: 'This is a discussion about the best anime series of the year.',
  heat_score: 85,
  source_metadata: { subreddit: 'r/anime', upvotes: 150 },
  fetched_at: '2024-12-01T10:00:00Z',
  translated_at: '2024-12-01T10:05:00Z',
  language: 'en',
}

const mockTranslationPendingItem: FeedItem = {
  id: 'test-2',
  source: 'steam',
  source_url: 'https://store.steampowered.com/app/test',
  translated_title: '[TRANSLATION_PENDING] Some Japanese Title',
  translated_body: '[TRANSLATION_PENDING] Some Japanese body text content.',
  heat_score: 42,
  source_metadata: { app_id: '12345' },
  fetched_at: '2024-12-01T11:00:00Z',
  translated_at: null,
  language: 'ja',
}

describe('FeedCard', () => {
  it('test_renders_all_fields', () => {
    render(<FeedCard item={mockFeedItem} />)

    // Source badge should show the source label
    expect(screen.getByText('Reddit')).toBeInTheDocument()

    // Title should be rendered
    expect(screen.getByText('Best Anime of 2024')).toBeInTheDocument()

    // Body should be rendered
    expect(screen.getByText('This is a discussion about the best anime series of the year.')).toBeInTheDocument()

    // Heat score should be rendered (85.0)
    expect(screen.getByText('85.0')).toBeInTheDocument()

    // View original button should be present
    expect(screen.getByText('▸ View original')).toBeInTheDocument()
  })

  it('test_translation_pending_badge', () => {
    render(<FeedCard item={mockTranslationPendingItem} />)

    // Source badge should show Steam
    expect(screen.getByText('Steam')).toBeInTheDocument()

    // Translation pending badge should be visible
    expect(screen.getByText('Translation pending')).toBeInTheDocument()

    // Title should have the [TRANSLATION_PENDING] prefix stripped
    expect(screen.getByText('Some Japanese Title')).toBeInTheDocument()
    expect(screen.queryByText('[TRANSLATION_PENDING] Some Japanese Title')).not.toBeInTheDocument()

    // Heat score should be rendered (42.0)
    expect(screen.getByText('42.0')).toBeInTheDocument()
  })

  it('test_view_original_collapsed', () => {
    render(<FeedCard item={mockFeedItem} />)

    // The "View original" button should be rendered initially (collapsed state)
    expect(screen.getByText('▸ View original')).toBeInTheDocument()

    // The URL link should NOT be visible yet
    expect(screen.queryByText('https://reddit.com/r/anime/test')).not.toBeInTheDocument()
  })
})
