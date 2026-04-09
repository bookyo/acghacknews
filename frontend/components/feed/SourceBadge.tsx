"use client"

import { Badge } from "@/components/ui/badge"
import { SOURCE_CONFIG } from "@/lib/constants"
import type { SourceName } from "@/lib/types"

export function SourceBadge({ source }: { source: SourceName }) {
  const config = SOURCE_CONFIG[source]
  return (
    <Badge variant="secondary" className={config.color}>
      {config.label}
    </Badge>
  )
}
