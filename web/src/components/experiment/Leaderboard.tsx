import { useState, useMemo } from 'react';
import type { LeaderboardEntry } from '../../api/types';

interface LeaderboardProps {
  entries: LeaderboardEntry[];
}

type SortKey = 'rank' | 'name' | 'portfolio_value' | 'returns_pct' | 'status';
type SortDirection = 'asc' | 'desc';

export function Leaderboard({ entries }: LeaderboardProps) {
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  const sortedEntries = useMemo(() => {
    const sorted = [...entries].sort((a, b) => {
      // Handle nullable returns_pct upfront
      let aVal: string | number = sortKey === 'returns_pct'
        ? (a.returns_pct ?? -Infinity)
        : (a[sortKey] as string | number);
      let bVal: string | number = sortKey === 'returns_pct'
        ? (b.returns_pct ?? -Infinity)
        : (b[sortKey] as string | number);

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      return sortDirection === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });

    return sorted;
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
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <div className="text-center">
          <p className="text-gray-500 font-medium">No agents to display</p>
          <p className="text-sm text-gray-400 mt-1">Leaderboard will appear after agents start trading</p>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'paused':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'eliminated':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getRankBadgeColor = (rank: number) => {
    if (rank === 1) return 'bg-brand-900 text-white shadow-lg shadow-brand-900/30';
    if (rank === 2) return 'bg-brand-800 text-white shadow-md shadow-brand-800/20';
    if (rank === 3) return 'bg-brand-700 text-white shadow-md shadow-brand-700/20';
    return 'bg-gray-200 text-gray-700';
  };

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="px-6 py-4 text-left">
                <button
                  onClick={() => handleSort('rank')}
                  className="flex items-center gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 transition-colors group"
                >
                  Rank
                  <SortIndicator active={sortKey === 'rank'} direction={sortDirection} />
                </button>
              </th>
              <th className="px-6 py-4 text-left">
                <button
                  onClick={() => handleSort('name')}
                  className="flex items-center gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 transition-colors group"
                >
                  Agent
                  <SortIndicator active={sortKey === 'name'} direction={sortDirection} />
                </button>
              </th>
              <th className="px-6 py-4 text-right">
                <button
                  onClick={() => handleSort('portfolio_value')}
                  className="flex items-center justify-end gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 transition-colors group ml-auto"
                >
                  Portfolio Value
                  <SortIndicator active={sortKey === 'portfolio_value'} direction={sortDirection} />
                </button>
              </th>
              <th className="px-6 py-4 text-right">
                <button
                  onClick={() => handleSort('returns_pct')}
                  className="flex items-center justify-end gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 transition-colors group ml-auto"
                >
                  Returns
                  <SortIndicator active={sortKey === 'returns_pct'} direction={sortDirection} />
                </button>
              </th>
              <th className="px-6 py-4 text-center">
                <button
                  onClick={() => handleSort('status')}
                  className="flex items-center justify-center gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 transition-colors group mx-auto"
                >
                  Status
                  <SortIndicator active={sortKey === 'status'} direction={sortDirection} />
                </button>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sortedEntries.map((entry, index) => (
              <tr
                key={entry.agent_id}
                className={`
                  transition-all duration-200 hover:bg-gray-50
                  ${entry.rank === 1 ? 'bg-brand-900/5 hover:bg-brand-900/10' : ''}
                `}
                style={{
                  animationDelay: `${index * 30}ms`,
                  animation: 'fadeSlideIn 0.4s ease-out forwards',
                  opacity: 0,
                }}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <span
                      className={`
                        inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold
                        transition-all duration-200
                        ${getRankBadgeColor(entry.rank)}
                      `}
                    >
                      {entry.rank}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-gray-900">{entry.name}</span>
                    <span className="text-xs text-gray-500 font-mono">{entry.agent_id}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className="text-sm font-semibold text-gray-900 font-mono tabular-nums">
                    ${entry.portfolio_value.toLocaleString('en-US', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  {entry.returns_pct !== null ? (
                    <span
                      className={`
                        inline-flex items-center gap-1 text-sm font-bold font-mono tabular-nums
                        ${entry.returns_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}
                      `}
                    >
                      {entry.returns_pct >= 0 ? '↑' : '↓'}
                      {entry.returns_pct >= 0 ? '+' : ''}
                      {entry.returns_pct.toFixed(2)}%
                    </span>
                  ) : (
                    <span className="text-sm text-gray-400">—</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="flex justify-center">
                    <span
                      className={`
                        inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border
                        ${getStatusColor(entry.status)}
                      `}
                    >
                      {entry.status}
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <style>{`
        @keyframes fadeSlideIn {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}

function SortIndicator({
  active,
  direction,
}: {
  active: boolean;
  direction: SortDirection;
}) {
  return (
    <span className={`transition-all ${active ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`}>
      {direction === 'asc' ? '↑' : '↓'}
    </span>
  );
}
