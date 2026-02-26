import { useState, useMemo, useEffect } from 'react';
import type { TransactionHistory } from '../../api/types';
import { Card } from '../ui/Card';
import { MetricCard } from '../ui/MetricCard';
import { Badge } from '../ui/Badge';

interface TransactionListProps {
  transactions?: TransactionHistory;
}

type SortField = 'date' | 'action' | 'symbol' | 'shares' | 'price' | 'total' | 'tax';
type SortDirection = 'asc' | 'desc';

export function TransactionList({ transactions }: TransactionListProps) {
  const [currentPage, setCurrentPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const pageSize = 20;

  // Reset pagination when transactions change
  useEffect(() => {
    setCurrentPage(0);
  }, [transactions]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  // Filter and sort transactions
  const filteredAndSorted = useMemo(() => {
    if (!transactions) return [];

    let filtered = transactions.transactions;

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((txn) =>
        txn.symbol.toLowerCase().includes(query)
      );
    }

    // Apply sorting
    const sorted = [...filtered].sort((a, b) => {
      let aVal: any;
      let bVal: any;

      switch (sortField) {
        case 'date':
          aVal = new Date(a.date).getTime();
          bVal = new Date(b.date).getTime();
          break;
        case 'action':
          aVal = a.action;
          bVal = b.action;
          break;
        case 'symbol':
          aVal = a.symbol;
          bVal = b.symbol;
          break;
        case 'shares':
          aVal = a.shares;
          bVal = b.shares;
          break;
        case 'price':
          aVal = a.price;
          bVal = b.price;
          break;
        case 'total':
          aVal = a.total;
          bVal = b.total;
          break;
        case 'tax':
          aVal = a.tax_paid ?? 0;
          bVal = b.tax_paid ?? 0;
          break;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [transactions, searchQuery, sortField, sortDirection]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSorted.length / pageSize);
  const startIdx = currentPage * pageSize;
  const endIdx = startIdx + pageSize;
  const currentTransactions = filteredAndSorted.slice(startIdx, endIdx);

  // Handle sort column click
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, default to descending
      setSortField(field);
      setSortDirection('desc');
    }
    setCurrentPage(0); // Reset to first page
  };

  // Sort indicator
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return (
        <svg className="w-3 h-3 ml-1 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return sortDirection === 'asc' ? (
      <svg className="w-3 h-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-3 h-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  if (!transactions) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No transaction data available
      </div>
    );
  }

  return (
    <div>
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <MetricCard
            label="Total Transactions"
            value={<span className="font-mono text-xl font-semibold">{transactions.transactions.length}</span>}
          />
        </Card>
        <Card>
          <MetricCard
            label="Buy Volume"
            value={<span className="font-mono text-xl font-semibold">{formatCurrency(transactions.total_buy_volume)}</span>}
          />
        </Card>
        <Card>
          <MetricCard
            label="Sell Volume"
            value={<span className="font-mono text-xl font-semibold">{formatCurrency(transactions.total_sell_volume)}</span>}
          />
        </Card>
        <Card>
          <MetricCard
            label="Total Tax Paid"
            value={<span className="font-mono text-xl font-semibold">{formatCurrency(transactions.total_tax_paid)}</span>}
          />
        </Card>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search by symbol..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(0); // Reset to first page on search
            }}
            className="w-full pl-10 pr-4 py-2 border border-border bg-card text-foreground rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          />
          {searchQuery && (
            <button
              onClick={() => {
                setSearchQuery('');
                setCurrentPage(0);
              }}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        {filteredAndSorted.length !== transactions.transactions.length && (
          <div className="mt-2 text-xs text-muted-foreground">
            Showing {filteredAndSorted.length} of {transactions.transactions.length} transactions
          </div>
        )}
      </div>

      {/* Transactions Table */}
      {filteredAndSorted.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          {searchQuery ? `No transactions found matching "${searchQuery}"` : 'No transactions yet'}
        </div>
      ) : (
        <>
          <div className="w-full border border-border rounded-xl overflow-hidden">
            <table className="w-full border-collapse bg-card">
              <thead>
                <tr>
                  <th
                    className="text-left text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('date')}
                  >
                    <div className="flex items-center">
                      Date
                      <SortIcon field="date" />
                    </div>
                  </th>
                  <th
                    className="text-left text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('action')}
                  >
                    <div className="flex items-center">
                      Action
                      <SortIcon field="action" />
                    </div>
                  </th>
                  <th
                    className="text-left text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('symbol')}
                  >
                    <div className="flex items-center">
                      Symbol
                      <SortIcon field="symbol" />
                    </div>
                  </th>
                  <th
                    className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('shares')}
                  >
                    <div className="flex items-center justify-end">
                      Shares
                      <SortIcon field="shares" />
                    </div>
                  </th>
                  <th
                    className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('price')}
                  >
                    <div className="flex items-center justify-end">
                      Price
                      <SortIcon field="price" />
                    </div>
                  </th>
                  <th
                    className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('total')}
                  >
                    <div className="flex items-center justify-end">
                      Total
                      <SortIcon field="total" />
                    </div>
                  </th>
                  <th
                    className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border cursor-pointer hover:bg-muted/80 transition-colors"
                    onClick={() => handleSort('tax')}
                  >
                    <div className="flex items-center justify-end">
                      Tax
                      <SortIcon field="tax" />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {currentTransactions.map((txn, idx) => (
                  <tr key={idx} className="border-b border-border/50 last:border-0 hover:bg-muted/50 transition-colors">
                    <td className="px-4 py-3.5 text-sm text-foreground">{txn.date}</td>
                    <td className="px-4 py-3.5">
                      <Badge
                        variant={txn.action.toLowerCase() === 'buy' ? 'success' : 'info'}
                        className="uppercase tracking-wide text-[0.6875rem] font-bold"
                      >
                        {txn.action}
                      </Badge>
                    </td>
                    <td className="px-4 py-3.5 font-mono font-bold text-sm text-foreground">{txn.symbol}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-sm text-foreground tabular-nums">
                      {txn.shares.toFixed(4)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-sm text-foreground tabular-nums">
                      {formatCurrency(txn.price)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-sm text-foreground tabular-nums">
                      {formatCurrency(txn.total)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-sm text-foreground tabular-nums">
                      {txn.tax_paid != null ? formatCurrency(txn.tax_paid) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-between items-center mt-4 px-4 py-3 bg-muted rounded-lg">
              <div className="text-sm text-muted-foreground">
                Page {currentPage + 1} of {totalPages} ({filteredAndSorted.length} total)
              </div>
              <div className="flex gap-2">
                <button
                  className="px-4 py-2 border border-border bg-card text-foreground text-sm font-medium rounded-md transition-colors hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={() => setCurrentPage(currentPage - 1)}
                  disabled={currentPage === 0}
                >
                  Previous
                </button>
                <button
                  className="px-4 py-2 border border-border bg-card text-foreground text-sm font-medium rounded-md transition-colors hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={() => setCurrentPage(currentPage + 1)}
                  disabled={currentPage === totalPages - 1}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
