"use client"

import { SOURCE_CONFIG } from "@/lib/constants"
import type { SourceName, SortOption } from "@/lib/types"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

const ALL_SOURCES: SourceName[] = ["reddit", "anilist", "steam", "anime_news"]

interface TopBarProps {
  activeSources: SourceName[]
  onSourcesChange: (sources: SourceName[]) => void
  activeSort: SortOption
  onSortChange: (sort: SortOption) => void
}

export function TopBar({
  activeSources,
  onSourcesChange,
  activeSort,
  onSortChange,
}: TopBarProps) {
  const toggleSource = (source: SourceName) => {
    if (activeSources.includes(source)) {
      onSourcesChange(activeSources.filter((s) => s !== source))
    } else {
      onSourcesChange([...activeSources, source])
    }
  }

  const SORT_OPTIONS: { value: SortOption; label: string }[] = [
    { value: "hot", label: "Hot" },
    { value: "new", label: "New" },
  ]

  return (
    <div data-testid="top-bar" className="border-b bg-background sticky top-0 z-10">
      <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
        {/* Left: Logo */}
        <h1 className="text-lg font-bold whitespace-nowrap">ACG Feed</h1>

        {/* Center: Source checkboxes */}
        <div className="flex items-center gap-3 flex-wrap justify-center">
          {ALL_SOURCES.map((source) => {
            const config = SOURCE_CONFIG[source]
            const isActive = activeSources.includes(source)
            return (
              <label
                key={source}
                className="flex items-center gap-1.5 cursor-pointer select-none"
              >
                <Checkbox
                  checked={isActive}
                  onCheckedChange={() => toggleSource(source)}
                />
                <span className={`text-sm hidden sm:inline ${config.color}`}>
                  {config.label}
                </span>
                {/* On small screens, show shorter label or just icon */}
                <span className={`text-sm sm:hidden ${config.color}`}>
                  {config.label.slice(0, 2)}
                </span>
              </label>
            )
          })}
        </div>

        {/* Right: Sort toggle */}
        <TooltipProvider>
          <div className="flex items-center gap-1 border rounded-lg p-0.5">
            {SORT_OPTIONS.map((opt) => (
              <Tooltip key={opt.value}>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => onSortChange(opt.value)}
                    className={`px-3 py-1 text-sm rounded-md transition-colors ${
                      activeSort === opt.value
                        ? "bg-primary text-primary-foreground font-medium"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {opt.label}
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Sort by {opt.label.toLowerCase()}est</p>
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        </TooltipProvider>
      </div>
    </div>
  )
}
