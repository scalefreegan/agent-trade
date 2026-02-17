import { useState, useMemo } from 'react';
import type { LeaderboardEntry } from '../../api/types';
import { Card } from '../ui/Card';
import { Badge, statusVariant } from '../ui/Badge';

interface LeaderboardProps {
  entries: LeaderboardEntry[];
}

type SortKey = 'rank' | 'name' | 'portfolio_value' | 'returns_pct' | 'status';
type SortDirection = 'asc' | 'desc';

export function Leaderboard({ entries }: LeaderboardProps) {
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  const sortedEntries = useMemo(() => {
    return [...entries].sort((a, b) => {
      const aVal: string | number = sortKey === 'returns_pct'
        ? (a.returns_pct ?? -Infinity)
        : (a[sortKey] as string | number);
      const bVal: string | number = sortKey === 'returns_pct'
        ? (b.returns_pct ?? -Infinity)
        : (b[sortKey] as string | number);

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDirection === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDirection === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });
  }, [entries, sortKey, sortDirection]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  if (entries.length === 0) {
    return (
      <Card>
        <div className="flex items-center justify-center h-40">
          <div className="text-center">
            <p className="text-muted-foreground font-medium">No agents to display</p>
            <p className="text-sm text-muted-foreground/60 mt-1">Leaderboard will appear after agents start trading</p>
          </div>
        </div>
      </Card>
    );
  }

  const getRankClasses = (rank: number) => {
    if (rank === 1) return 'bg-brand-900 text-white shadow-lg shadow-brand-900/30';
    if (rank === 2) return 'bg-brand-800 text-white shadow-md shadow-brand-800/20';
    if (rank === 3) return 'bg-brand-700 text-white shadow-md shadow-brand-700/20';
    return 'bg-muted text-muted-foreground';
  };

  return (
    <Card padding={false}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {(['rank', 'name', 'portfolio_value', 'returns_pct', 'status'] as const).map((key) => {
                const labels: Record<typeof key, string> = {
                  rank: 'Rank',
                  name: 'Agent',
                  portfolio_value: 'Portfolio Value',
                  returns_pct: 'Returns',
                  status: 'Status',
                };
                const isRight = key === 'portfolio_value' || key === 'returns_pct';
                const isCenter = key === 'status';
                return (
                  <th
                    key={key}
                    className={`px-6 py-4 ${isRight ? 'text-right' : isCenter ? 'text-center' : 'text-left'}`}
                  >
                    <button
                      type="button"
                      onClick={() => handleSort(key)}
                      className={`flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors group ${isRight ? 'ml-auto' : isCenter ? 'mx-auto' : ''}`}
                    >
                      {labels[key]}
                      <SortIndicator active={sortKey === key} direction={sortDirection} />
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {sortedEntries.map((entry, index) => (
              <tr
                key={entry.agent_id}
                className={`transition-colors hover:bg-muted/30 animate-fade-in ${entry.rank === 1 ? 'bg-primary/5 hover:bg-primary/10' : ''}`}
                style={{ animationDelay: `${index * 30}ms` }}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold transition-all ${getRankClasses(entry.rank)}`}
                  >
                    {entry.rank}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-foreground">{entry.name}</span>
                    <span className="text-xs text-muted-foreground font-mono">{entry.agent_id}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className="text-sm font-semibold text-foreground font-mono tabular-nums">
                    ${entry.portfolio_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  {entry.returns_pct !== null ? (
                    <span
                      className={`inline-flex items-center gap-1 text-sm font-bold font-mono tabular-nums ${entry.returns_pct >= 0 ? 'text-gain' : 'text-loss'}`}
                    >
                      {entry.returns_pct >= 0 ? '↑' : '↓'}
                      {entry.returns_pct >= 0 ? '+' : ''}
                      {entry.returns_pct.toFixed(2)}%
                    </span>
                  ) : (
                    <span className="text-sm text-muted-foreground">—</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="flex justify-center">
                    <Badge variant={statusVariant(entry.status)}>
                      {entry.status}
                    </Badge>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function SortIndicator({ active, direction }: { active: boolean; direction: SortDirection }) {
  return (
    <span className={`transition-all ${active ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`}>
      {direction === 'asc' ? '↑' : '↓'}
    </span>
  );
}
