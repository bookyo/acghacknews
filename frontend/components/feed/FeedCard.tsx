"use client"

import type { FeedItem, Language } from "@/lib/types"
import { SourceBadge } from "./SourceBadge"
import { HeatScore } from "./HeatScore"
import { ViewOriginal } from "./ViewOriginal"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle } from "lucide-react"

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)
  const diffWeeks = Math.floor(diffDays / 7)
  const diffMonths = Math.floor(diffDays / 30)

  if (diffSeconds < 60) return "just now"
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes !== 1 ? "s" : ""} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`
  if (diffWeeks < 4) return `${diffWeeks} week${diffWeeks !== 1 ? "s" : ""} ago`
  return `${diffMonths} month${diffMonths !== 1 ? "s" : ""} ago`
}

const TRANSLATION_PENDING_PREFIX = "[TRANSLATION_PENDING]"

interface FeedCardProps {
  item: FeedItem
  language: Language
}

export function FeedCard({ item, language }: FeedCardProps) {
  const isEn = language === "en"

  // Determine title
  let displayTitle: string
  if (isEn) {
    displayTitle = item.original_title
  } else {
    const isTranslationPending = item.translated_title.startsWith(TRANSLATION_PENDING_PREFIX)
    displayTitle = isTranslationPending
      ? item.translated_title.slice(TRANSLATION_PENDING_PREFIX.length).trim()
      : item.translated_title
  }

  // Determine body
  const displayBody = isEn ? item.original_body : item.translated_body

  const isTranslationPending = !isEn && item.translated_title.startsWith(TRANSLATION_PENDING_PREFIX)

  return (
    <div data-testid="feed-card" className="rounded-lg border p-4 space-y-2 hover:bg-accent/50 transition-colors">
      <div className="flex items-center gap-2 flex-wrap">
        <SourceBadge source={item.source} />
        {isTranslationPending && (
          <Badge variant="outline" className="text-yellow-600 border-yellow-500/30 bg-yellow-500/10 gap-1">
            <AlertTriangle className="h-3 w-3" />
            Translation pending
          </Badge>
        )}
      </div>
      <h3 className="font-semibold text-base leading-tight">{displayTitle}</h3>
      {displayBody && (
        <p className="text-sm text-muted-foreground line-clamp-3">{displayBody}</p>
      )}
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <HeatScore score={item.heat_score} />
        <span className="text-xs">{formatRelativeTime(item.fetched_at)}</span>
      </div>
      <ViewOriginal url={item.source_url} />
    </div>
  )
}
