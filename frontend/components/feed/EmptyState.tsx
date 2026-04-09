export function EmptyState({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="text-lg text-muted-foreground">
        {message || "No items yet. The next fetch is coming soon."}
      </p>
    </div>
  )
}
