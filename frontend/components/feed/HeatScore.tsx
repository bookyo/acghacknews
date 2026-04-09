"use client"

import { Flame } from "lucide-react"

export function HeatScore({ score }: { score: number }) {
  return (
    <span className="flex items-center gap-1 text-sm text-muted-foreground">
      <Flame className="h-4 w-4 text-orange-500" />
      {score.toFixed(1)}
    </span>
  )
}
