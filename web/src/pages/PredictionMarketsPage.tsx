import { useState, useMemo, useEffect } from 'react';
import { useKalshiEvents, useKalshiSeriesList, buildSeriesSlugMap, type KalshiEvent } from '../api/kalshi';
import { EventCard } from '../components/predictions/EventCard';
import { SortControls, type SortOption, type MaxDateRange } from '../components/predictions/SortControls';

export function PredictionMarketsPage() {
  const [sortBy, setSortBy] = useState<SortOption>('volume_24h');
  const [statusFilter, setStatusFilter] = useState('open');
  const [maxDateRange, setMaxDateRange] = useState<MaxDateRange>('none');
  const [searchQuery, setSearchQuery] = useState('');
  const [category, setCategory] = useState('');
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allEvents, setAllEvents] = useState<KalshiEvent[]>([]);

  const { data: seriesData } = useKalshiSeriesList();
  const seriesSlugMap = useMemo(
    () => buildSeriesSlugMap(seriesData?.series ?? []),
    [seriesData],
  );

  const { data, isLoading, error, isFetching } = useKalshiEvents({
    status: statusFilter || undefined,
    limit: 200,
    cursor,
  });

  // Accumulate events from all loaded pages
  useEffect(() => {
    if (!data?.events || error) return;

    if (cursor) {
      setAllEvents((prev) => [...prev, ...data.events]);
    } else {
      setAllEvents(data.events);
    }
  }, [data, cursor, error]);

  // Helper: aggregate volume_24h for an event
  const eventVolume24h = (e: KalshiEvent) =>
    (e.markets ?? []).reduce((sum, m) => sum + (m.volume_24h || 0), 0);
  const eventVolume = (e: KalshiEvent) =>
    (e.markets ?? []).reduce((sum, m) => sum + (m.volume || 0), 0);
  const eventOI = (e: KalshiEvent) =>
    (e.markets ?? []).reduce((sum, m) => sum + (m.open_interest || 0), 0);
  const eventEarliestClose = (e: KalshiEvent): Date | null =>
    (e.markets ?? []).reduce<Date | null>((earliest, m) => {
      const d = new Date(m.close_time);
      if (isNaN(d.getTime())) return earliest;
      return earliest === null || d < earliest ? d : earliest;
    }, null);
  const eventLatestCreated = (e: KalshiEvent): Date =>
    (e.markets ?? []).reduce((latest, m) => {
      const d = new Date(m.created_time);
      return d > latest ? d : latest;
    }, new Date(0));

  // Client-side filtering and sorting
  const displayedEvents = useMemo(() => {
    let events = allEvents;

    // Category filter
    if (category) {
      events = events.filter((e) => e.category === category);
    }

    // Date range filter (client-side using earliest market close_time)
    if (maxDateRange !== 'none') {
      const cutoff = new Date();
      switch (maxDateRange) {
        case '1m': cutoff.setMonth(cutoff.getMonth() + 1); break;
        case '3m': cutoff.setMonth(cutoff.getMonth() + 3); break;
        case '6m': cutoff.setMonth(cutoff.getMonth() + 6); break;
        case '1y': cutoff.setFullYear(cutoff.getFullYear() + 1); break;
      }
      events = events.filter((e) => {
        const close = eventEarliestClose(e);
        return close !== null && close.getTime() <= cutoff.getTime();
      });
    }

    // Text search filter
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      events = events.filter(
        (e) =>
          e.title.toLowerCase().includes(q) ||
          (e.sub_title && e.sub_title.toLowerCase().includes(q)) ||
          (e.markets ?? []).some(
            (m) =>
              (m.yes_sub_title && m.yes_sub_title.toLowerCase().includes(q)) ||
              m.title.toLowerCase().includes(q)
          )
      );
    }

    // Sort
    const sorted = [...events];
    switch (sortBy) {
      case 'volume_24h':
        return sorted.sort((a, b) => eventVolume24h(b) - eventVolume24h(a));
      case 'volume':
        return sorted.sort((a, b) => eventVolume(b) - eventVolume(a));
      case 'open_interest':
        return sorted.sort((a, b) => eventOI(b) - eventOI(a));
      case 'close_time': {
        return sorted.sort((a, b) => {
          const ca = eventEarliestClose(a);
          const cb = eventEarliestClose(b);
          if (!ca && !cb) return 0;
          if (!ca) return 1;
          if (!cb) return -1;
          return ca.getTime() - cb.getTime();
        });
      }
      case 'created_time':
        return sorted.sort(
          (a, b) => eventLatestCreated(b).getTime() - eventLatestCreated(a).getTime()
        );
      default: {
        const _exhaustive: never = sortBy;
        void _exhaustive;
        return sorted;
      }
    }
  }, [allEvents, sortBy, searchQuery, category, maxDateRange]);

  const resetPagination = () => {
    setCursor(undefined);
    setAllEvents([]);
  };

  const handleSortChange = (newSort: SortOption) => {
    setSortBy(newSort);
  };

  const handleStatusFilterChange = (newStatus: string) => {
    setStatusFilter(newStatus);
    resetPagination();
  };

  const handleMaxDateRangeChange = (newRange: MaxDateRange) => {
    setMaxDateRange(newRange);
  };

  const handleCategoryChange = (newCategory: string) => {
    setCategory(newCategory);
  };

  const handleLoadMore = () => {
    if (data?.cursor) {
      setCursor(data.cursor);
    }
  };

  const hasMore = !!data?.cursor;

  // Collect unique categories from events
  const categories = useMemo(() => {
    const cats = new Set<string>();
    allEvents.forEach((e) => {
      if (e.category) cats.add(e.category);
    });
    return Array.from(cats).sort();
  }, [allEvents]);

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
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        category={category}
        onCategoryChange={handleCategoryChange}
        categories={categories}
      />

      {/* Result count */}
      {allEvents.length > 0 && (
        <p className="text-sm text-muted-foreground">
          {displayedEvents.length === allEvents.length
            ? `${allEvents.length} events loaded`
            : `${displayedEvents.length} events matching filters (${allEvents.length} loaded)`}
        </p>
      )}

      {/* Loading skeleton */}
      {isLoading && allEvents.length === 0 && (
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

      {/* Events grid */}
      {!isLoading && !error && displayedEvents.length === 0 && (
        <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
          No events found
        </div>
      )}

      {displayedEvents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {displayedEvents.map((event) => (
            <EventCard key={event.event_ticker} event={event} seriesSlugMap={seriesSlugMap} />
          ))}
        </div>
      )}

      {/* Load more button */}
      {hasMore && displayedEvents.length > 0 && (
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
