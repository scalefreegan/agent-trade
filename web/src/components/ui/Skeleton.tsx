interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded bg-gray-200 dark:bg-gray-700 ${className}`}
      aria-hidden="true"
    />
  );
}

export function ExperimentCardSkeleton() {
  return (
    <div
      className="bg-white dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 p-6 animate-pulse"
      aria-hidden="true"
    >
      {/* Title + badge row */}
      <div className="flex items-start justify-between mb-5">
        <Skeleton className="h-5 w-40 rounded" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>

      {/* Detail rows */}
      <div className="space-y-3">
        {[40, 32, 28].map((w, i) => (
          <div key={i} className="flex justify-between items-center">
            <Skeleton className="h-3.5 w-20" />
            <Skeleton className={`h-3.5 w-${w === 40 ? '28' : w === 32 ? '16' : '12'}`} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function LeaderboardSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 overflow-hidden animate-pulse">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-3 flex gap-6">
        {[8, 24, 20, 20, 16].map((w, i) => (
          <Skeleton key={i} className={`h-3 w-${w}`} />
        ))}
      </div>

      {/* Rows */}
      {Array.from({ length: 5 }).map((_, row) => (
        <div
          key={row}
          className="px-6 py-4 flex gap-6 items-center border-b border-gray-100 dark:border-gray-800 last:border-0"
          style={{ opacity: 1 - row * 0.12 }}
        >
          <Skeleton className="h-4 w-5 rounded" />
          <Skeleton className="h-4 w-32 rounded" />
          <Skeleton className="h-4 w-24 rounded ml-auto" />
          <Skeleton className="h-4 w-16 rounded" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div
      className="w-full bg-white dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 p-6 animate-pulse"
      style={{ height: 300 }}
      aria-hidden="true"
    >
      {/* Y-axis labels */}
      <div className="flex h-full gap-4">
        <div className="flex flex-col justify-between py-2 w-12">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-3 w-10" />
          ))}
        </div>

        {/* Chart body */}
        <div className="flex-1 flex flex-col gap-2 justify-end">
          {/* Fake sparkline bars */}
          <div className="flex items-end gap-1 h-48">
            {Array.from({ length: 20 }).map((_, i) => {
              const pct = 30 + Math.sin(i * 0.7) * 20 + Math.cos(i * 0.3) * 15 + Math.random() * 10;
              return (
                <div
                  key={i}
                  className="flex-1 rounded-t bg-gray-200 dark:bg-gray-700"
                  style={{ height: `${pct}%` }}
                />
              );
            })}
          </div>

          {/* X-axis labels */}
          <div className="flex justify-between pt-2 border-t border-gray-100 dark:border-gray-800">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-3 w-8" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
