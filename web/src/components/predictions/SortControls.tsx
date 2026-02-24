export type SortOption =
  | 'volume_24h'
  | 'volume'
  | 'open_interest'
  | 'yes_bid'
  | 'close_time'
  | 'created_time';

interface SortControlsProps {
  sortBy: SortOption;
  onSortChange: (sort: SortOption) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
}

const sortOptions: { value: SortOption; label: string }[] = [
  { value: 'volume_24h', label: 'Volume (24h)' },
  { value: 'volume', label: 'Total Volume' },
  { value: 'open_interest', label: 'Open Interest' },
  { value: 'yes_bid', label: 'Yes Price' },
  { value: 'close_time', label: 'Ending Soon' },
  { value: 'created_time', label: 'Newest' },
];

const statusOptions = [
  { value: 'open', label: 'Open' },
  { value: '', label: 'All' },
];

export function SortControls({
  sortBy,
  onSortChange,
  statusFilter,
  onStatusFilterChange,
}: SortControlsProps) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Sort dropdown */}
      <div className="flex items-center gap-2">
        <label htmlFor="sort" className="text-sm font-medium text-foreground">
          Sort by:
        </label>
        <select
          id="sort"
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value as SortOption)}
          className="px-3 py-1.5 text-sm bg-card text-foreground border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
        >
          {sortOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Status filter */}
      <div className="flex items-center gap-2">
        <label htmlFor="status" className="text-sm font-medium text-foreground">
          Status:
        </label>
        <select
          id="status"
          value={statusFilter}
          onChange={(e) => onStatusFilterChange(e.target.value)}
          className="px-3 py-1.5 text-sm bg-card text-foreground border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
        >
          {statusOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
