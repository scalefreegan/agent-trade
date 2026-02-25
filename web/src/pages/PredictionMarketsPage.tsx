import { useState, useMemo, useEffect } from 'react';
import { useKalshiEvents, type KalshiMarket } from '../api/kalshi';
import { MarketCard } from '../components/predictions/MarketCard';
import { SortControls, type SortOption, type MaxDateRange } from '../components/predictions/SortControls';

function getMaxCloseDate(range: MaxDateRange): Date | null {
  if (range === 'none') return null;
  const now = new Date();
  switch (range) {
    case '1m':
      now.setMonth(now.getMonth() + 1);
      return now;
    case '3m':
      now.setMonth(now.getMonth() + 3);
      return now;
    case '6m':
      now.setMonth(now.getMonth() + 6);
      return now;
    case '1y':
      now.setFullYear(now.getFullYear() + 1);
      return now;
  }
}

export function PredictionMarketsPage() {
  const [sortBy, setSortBy] = useState<SortOption>('volume_24h');
  const [statusFilter, setStatusFilter] = useState('open');
  const [maxDateRange, setMaxDateRange] = useState<MaxDateRange>('6m');
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allMarkets, setAllMarkets] = useState<KalshiMarket[]>([]);

  const { data, isLoading, error, isFetching } = useKalshiEvents({
    status: statusFilter || undefined,
    limit: 20,
    cursor,
    with_nested_markets: true,
  });

  // Accumulate markets from all loaded pages
  useEffect(() => {
    if (!data?.events || error) return;

    const newMarkets = data.events.flatMap((event) =>
      (event.markets || []).map((market) => ({
        ...market,
        eventTicker: event.ticker,
        eventTitle: event.title,
      }))
    );
    if (cursor) {
      // Append to existing markets
      setAllMarkets((prev) => [...prev, ...newMarkets]);
    } else {
      // Reset markets (new filter/sort)
      setAllMarkets(newMarkets);
    }
  }, [data, cursor, error]);

  // Client-side filtering and sorting — reacts to all filter/sort state changes
  const displayedMarkets = useMemo(() => {
    // Filter by max close date
    const maxDate = getMaxCloseDate(maxDateRange);
    let markets = allMarkets;
    if (maxDate) {
      const maxTime = maxDate.getTime();
      markets = markets.filter((m) => {
        const closeTime = new Date(m.close_time).getTime();
        return !isNaN(closeTime) && closeTime <= maxTime;
      });
    }

    // Sort
    const sorted = [...markets];
    switch (sortBy) {
      case 'volume_24h':
        return sorted.sort((a, b) => (b.volume_24h || 0) - (a.volume_24h || 0));
      case 'volume':
        return sorted.sort((a, b) => (b.volume || 0) - (a.volume || 0));
      case 'open_interest':
        return sorted.sort((a, b) => (b.open_interest || 0) - (a.open_interest || 0));
      case 'yes_bid':
        return sorted.sort((a, b) => (b.yes_bid || 0) - (a.yes_bid || 0));
      case 'close_time':
        return sorted.sort(
          (a, b) => new Date(a.close_time).getTime() - new Date(b.close_time).getTime()
        );
      case 'created_time':
        return sorted.sort(
          (a, b) => new Date(b.created_time).getTime() - new Date(a.created_time).getTime()
        );
      default: {
        const _exhaustive: never = sortBy;
        return sorted;
      }
    }
  }, [allMarkets, sortBy, maxDateRange]);

  const resetPagination = () => {
    setCursor(undefined);
    setAllMarkets([]);
  };

  const handleSortChange = (newSort: SortOption) => {
    setSortBy(newSort);
    resetPagination();
  };

  const handleStatusFilterChange = (newStatus: string) => {
    setStatusFilter(newStatus);
    resetPagination();
  };

  const handleMaxDateRangeChange = (newRange: MaxDateRange) => {
    setMaxDateRange(newRange);
    resetPagination();
  };

  const handleLoadMore = () => {
    if (data?.cursor) {
      setCursor(data.cursor);
    }
  };

  const hasMore = !!data?.cursor;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Prediction Markets</h1>
      </div>

      {/* Controls */}
      <SortControls
        sortBy={sortBy}
        onSortChange={handleSortChange}
        statusFilter={statusFilter}
        onStatusFilterChange={handleStatusFilterChange}
        maxDateRange={maxDateRange}
        onMaxDateRangeChange={handleMaxDateRangeChange}
      />

      {/* Loading skeleton */}
      {isLoading && allMarkets.length === 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="animate-pulse bg-card rounded-xl border border-border p-6"
            >
              <div className="h-6 bg-muted rounded w-3/4 mb-3" />
              <div className="h-4 bg-muted rounded w-1/2 mb-4" />
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="h-12 bg-muted rounded" />
                <div className="h-12 bg-muted rounded" />
              </div>
              <div className="h-4 bg-muted rounded w-full" />
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-loss/10 border border-loss/20 rounded-lg p-4 text-loss text-sm">
          Failed to load prediction markets. Please try again later.
          <div className="text-xs mt-1 opacity-75">
            {error instanceof Error ? error.message : String(error)}
          </div>
        </div>
      )}

      {/* Markets grid */}
      {!isLoading && !error && displayedMarkets.length === 0 && (
        <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
          No markets found
        </div>
      )}

      {displayedMarkets.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {displayedMarkets.map((market) => (
            <MarketCard key={market.ticker} market={market} />
          ))}
        </div>
      )}

      {/* Load more button */}
      {hasMore && displayedMarkets.length > 0 && (
        <div className="flex justify-center pt-4">
          <button
            onClick={handleLoadMore}
            disabled={isFetching}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {isFetching ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  );
}
