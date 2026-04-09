import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { FeedList } from '../components/feed/FeedList'
import type { FeedItem, FeedResponse } from '../lib/types'

const mockItems: FeedItem[] = [
  {
    id: 'item-1',
    source: 'reddit',
    source_url: 'https://reddit.com/r/anime/1',
    translated_title: 'First Post',
    translated_body: 'Body of first post.',
    heat_score: 90,
    source_metadata: {},
    fetched_at: '2024-12-01T10:00:00Z',
    translated_at: '2024-12-01T10:05:00Z',
    language: 'en',
  },
  {
    id: 'item-2',
    source: 'anilist',
    source_url: 'https://anilist.co/2',
    translated_title: 'Second Post',
    translated_body: 'Body of second post.',
    heat_score: 75,
    source_metadata: {},
    fetched_at: '2024-12-01T11:00:00Z',
    translated_at: '2024-12-01T11:05:00Z',
    language: 'en',
  },
]

const mockResponse: FeedResponse = {
  items: mockItems,
  total: 2,
  page: 1,
  per_page: 20,
  has_next: false,
}

// Mock the api module
vi.mock('../lib/api', () => ({
  getFeed: vi.fn(),
}))

import { getFeed } from '../lib/api'
const mockedGetFeed = vi.mocked(getFeed)

describe('FeedList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('test_shows_loading_skeleton', async () => {
    // Delay the API response so we can see the loading state
    let resolvePromise: (value: FeedResponse) => void
    const pendingPromise = new Promise<FeedResponse>((resolve) => {
      resolvePromise = resolve
    })
    mockedGetFeed.mockReturnValue(pendingPromise)

    render(<FeedList sources={['reddit', 'anilist']} sort="hot" />)

    // While loading, skeleton elements should be present (animate-pulse divs)
    const skeletonElements = document.querySelectorAll('.animate-pulse')
    expect(skeletonElements.length).toBeGreaterThan(0)

    // Resolve the promise to clean up
    resolvePromise!(mockResponse)
    await waitFor(() => {
      expect(screen.getByTestId('feed-list')).toBeInTheDocument()
    })
  })

  it('test_shows_empty_state', async () => {
    const emptyResponse: FeedResponse = {
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
      has_next: false,
    }
    mockedGetFeed.mockResolvedValue(emptyResponse)

    render(<FeedList sources={['reddit']} sort="hot" />)

    await waitFor(() => {
      expect(screen.getByText('No items yet. The next fetch is coming soon.')).toBeInTheDocument()
    })
  })

  it('test_shows_items', async () => {
    mockedGetFeed.mockResolvedValue(mockResponse)

    render(<FeedList sources={['reddit', 'anilist']} sort="hot" />)

    // Wait for items to load
    await waitFor(() => {
      expect(screen.getByText('First Post')).toBeInTheDocument()
    })

    expect(screen.getByText('Second Post')).toBeInTheDocument()
    expect(screen.getByText('Reddit')).toBeInTheDocument()
    expect(screen.getByText('AniList')).toBeInTheDocument()
    expect(screen.getByText('90.0')).toBeInTheDocument()
    expect(screen.getByText('75.0')).toBeInTheDocument()
  })
})
