import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TopBar } from '../components/layout/TopBar'
import type { SourceName, SortOption } from '../lib/types'

const defaultProps = {
  activeSources: ['reddit', 'anilist', 'steam', 'anime_news'] as SourceName[],
  onSourcesChange: vi.fn(),
  activeSort: 'hot' as SortOption,
  onSortChange: vi.fn(),
}

describe('TopBar', () => {
  it('test_source_filter_checkboxes', () => {
    render(<TopBar {...defaultProps} />)

    // Logo should be rendered
    expect(screen.getByText('ACG Feed')).toBeInTheDocument()

    // Source labels should be rendered (they appear on sm+ screens)
    expect(screen.getByText('Reddit')).toBeInTheDocument()
    expect(screen.getByText('AniList')).toBeInTheDocument()
    expect(screen.getByText('Steam')).toBeInTheDocument()
    expect(screen.getByText('Anime News')).toBeInTheDocument()

    // The top bar container should exist
    expect(screen.getByTestId('top-bar')).toBeInTheDocument()
  })

  it('test_sort_toggle', () => {
    render(<TopBar {...defaultProps} />)

    // Sort toggle buttons should be rendered
    expect(screen.getByText('Hot')).toBeInTheDocument()
    expect(screen.getByText('New')).toBeInTheDocument()
  })
})
