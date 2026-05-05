import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TabBar } from '../components/layout/TabBar'

describe('TabBar', () => {
  it('test_feed_tab_active', () => {
    render(<TabBar />)

    // All tabs should be rendered
    expect(screen.getByText('Feed')).toBeInTheDocument()
    expect(screen.getByText('Social')).toBeInTheDocument()
    expect(screen.getByText('Search')).toBeInTheDocument()
    expect(screen.getByText('vbot')).toBeInTheDocument()

    // Tab bar container should exist
    expect(screen.getByTestId('tab-bar')).toBeInTheDocument()

    // Feed tab should be active (it's a button that is not disabled)
    const feedButton = screen.getByText('Feed').closest('button')!
    expect(feedButton.disabled).toBe(false)
  })

  it('test_disabled_tabs_visible', () => {
    render(<TabBar />)

    // Social and Search tabs should be visible but disabled
    const socialButton = screen.getByText('Social').closest('button')!
    const searchButton = screen.getByText('Search').closest('button')!

    expect(socialButton.disabled).toBe(true)
    expect(searchButton.disabled).toBe(true)
  })

  it('test_vbot_link', () => {
    render(<TabBar />)

    const vbotLink = screen.getByRole('link', { name: 'vbot' })

    expect(vbotLink).toHaveAttribute('href', 'https://vbot.reelbit.cc')
    expect(vbotLink).toHaveAttribute('target', '_blank')
  })
})
