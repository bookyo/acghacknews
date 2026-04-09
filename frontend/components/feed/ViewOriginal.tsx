"use client"

import { useState } from "react"
import { ExternalLink } from "lucide-react"

export function ViewOriginal({ url }: { url: string }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="mt-2">
      {!expanded ? (
        <button
          onClick={() => setExpanded(true)}
          className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          ▸ View original
        </button>
      ) : (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-500 hover:underline flex items-center gap-1"
        >
          <ExternalLink className="h-3 w-3" />
          {url}
        </a>
      )}
    </div>
  )
}
