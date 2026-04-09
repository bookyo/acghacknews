"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import type { SourceName, SortOption, FeedItem } from "@/lib/types"
import { getFeed } from "@/lib/api"
import { FeedCard } from "./FeedCard"
import { LoadingSkeleton } from "./LoadingSkeleton"
import { EmptyState } from "./EmptyState"

interface FeedListProps {
  sources: SourceName[]
  sort: SortOption
}

export function FeedList({ sources, sort }: FeedListProps) {
  const [items, setItems] = useState<FeedItem[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const sentinelRef = useRef<HTMLDivElement>(null)
  const isFetchingRef = useRef(false)

  const fetchItems = useCallback(
    async (pageNum: number, reset: boolean) => {
      if (isFetchingRef.current) return
      isFetchingRef.current = true

      if (reset) {
        setLoading(true)
      }

      try {
        // Fetch all items with source filter if specific sources are selected
        // The API only supports single source at a time, so we fetch without source
        // and filter client-side, or fetch the first selected source.
        // For simplicity, fetch without source filter (all sources) and filter client-side.
        const response = await getFeed({
          page: pageNum,
          sort,
        })

        let filtered = response.items
        if (sources.length > 0) {
          filtered = response.items.filter((item) => sources.includes(item.source))
        }

        setItems((prev) => (reset ? filtered : [...prev, ...filtered]))
        setHasMore(response.has_next && filtered.length > 0)
        setPage(pageNum)
      } catch (error) {
        console.error("Failed to fetch feed:", error)
        if (reset) {
          setItems([])
        }
      } finally {
        setLoading(false)
        isFetchingRef.current = false
      }
    },
    [sources, sort]
  )

  // Re-fetch when sources or sort changes
  useEffect(() => {
    fetchItems(1, true)
  }, [fetchItems])

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (entry.isIntersecting && hasMore && !loading && !isFetchingRef.current) {
          fetchItems(page + 1, false)
        }
      },
      { rootMargin: "200px" }
    )

    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [hasMore, loading, page, fetchItems])

  if (loading && items.length === 0) {
    return <LoadingSkeleton count={10} />
  }

  if (!loading && items.length === 0) {
    return <EmptyState />
  }

  return (
    <div data-testid="feed-list" className="space-y-4">
      {items.map((item) => (
        <FeedCard key={item.id} item={item} />
      ))}
      <div ref={sentinelRef} className="h-1" />
      {loading && items.length > 0 && <LoadingSkeleton count={3} />}
    </div>
  )
}
