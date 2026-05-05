"use client"

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface Tab {
  id: string
  label: string
  active: boolean
  disabled: boolean
  href?: string
}

const TABS: Tab[] = [
  { id: "feed", label: "Feed", active: true, disabled: false },
  { id: "social", label: "Social", active: false, disabled: true },
  { id: "search", label: "Search", active: false, disabled: true },
  { id: "vbot", label: "vbot", active: false, disabled: false, href: "https://vbot.reelbit.cc" },
]

export function TabBar() {
  return (
    <TooltipProvider>
      <nav data-testid="tab-bar" className="border-b bg-background">
        <div className="max-w-3xl mx-auto px-4 flex gap-6">
          {TABS.map((tab) => {
            const className = `py-3 text-sm font-medium transition-colors border-b-2 ${
              tab.active
                ? "border-primary text-foreground"
                : tab.disabled
                ? "border-transparent text-muted-foreground/50 cursor-not-allowed"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground"
            }`

            if (tab.href) {
              return (
                <a
                  key={tab.id}
                  href={tab.href}
                  target="_blank"
                  rel="noreferrer"
                  className={className}
                >
                  {tab.label}
                </a>
              )
            }

            const button = (
              <button
                key={tab.id}
                disabled={tab.disabled}
                className={className}
              >
                {tab.label}
              </button>
            )

            if (tab.disabled) {
              return (
                <Tooltip key={tab.id}>
                  <TooltipTrigger asChild>{button}</TooltipTrigger>
                  <TooltipContent>
                    <p>Coming soon</p>
                  </TooltipContent>
                </Tooltip>
              )
            }

            return button
          })}
        </div>
      </nav>
    </TooltipProvider>
  )
}
