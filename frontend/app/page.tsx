"use client"

import { useState } from "react"
import type { SourceName, SortOption, Language } from "@/lib/types"
import { TabBar } from "@/components/layout/TabBar"
import { TopBar } from "@/components/layout/TopBar"
import { FeedList } from "@/components/feed/FeedList"

const ALL_SOURCES: SourceName[] = ["reddit", "anilist", "steam", "anime_news"]

export default function Home() {
  const [activeSources, setActiveSources] = useState<SourceName[]>(ALL_SOURCES)
  const [activeSort, setActiveSort] = useState<SortOption>("hot")
  const [language, setLanguage] = useState<Language>("zh")

  return (
    <div className="min-h-screen bg-background">
      <TabBar />
      <TopBar
        activeSources={activeSources}
        onSourcesChange={setActiveSources}
        activeSort={activeSort}
        onSortChange={setActiveSort}
        language={language}
        onLanguageChange={setLanguage}
      />
      <main className="max-w-3xl mx-auto px-4 py-6">
        <FeedList sources={activeSources} sort={activeSort} language={language} />
      </main>
    </div>
  )
}
