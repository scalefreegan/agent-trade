import { useState } from 'react';
import type { TransactionHistory as TransactionHistoryType } from '../../api/types';
import { Card } from '../ui/Card';
import { MetricCard } from '../ui/MetricCard';
import { Badge } from '../ui/Badge';

interface TransactionHistoryProps {
  history: TransactionHistoryType;
}

export function TransactionHistory({ history }: TransactionHistoryProps) {
  const [currentPage, setCurrentPage] = useState(0);
  const pageSize = 20;

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const totalPages = Math.ceil(history.transactions.length / pageSize);
  const startIdx = currentPage * pageSize;
  const endIdx = startIdx + pageSize;
  const currentTransactions = history.transactions.slice(startIdx, endIdx);

  return (
    <div>
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <MetricCard label="Total Transactions" value={<span className="font-mono text-xl font-semibold">{history.transactions.length}</span>} />
        </Card>
        <Card>
          <MetricCard label="Buy Volume" value={<span className="font-mono text-xl font-semibold">{formatCurrency(history.total_buy_volume)}</span>} />
        </Card>
        <Card>
          <MetricCard label="Sell Volume" value={<span className="font-mono text-xl font-semibold">{formatCurrency(history.total_sell_volume)}</span>} />
        </Card>
        <Card>
          <MetricCard label="Total Tax Paid" value={<span className="font-mono text-xl font-semibold">{formatCurrency(history.total_tax_paid)}</span>} />
        </Card>
      </div>

      {/* Transactions Table */}
      {history.transactions.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">No transactions yet</div>
      ) : (
        <>
          <div className="w-full border border-border rounded-xl overflow-hidden">
            <table className="w-full border-collapse bg-card">
              <thead>
                <tr>
                  <th className="text-left text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border">Date</th>
                  <th className="text-left text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border">Action</th>
                  <th className="text-left text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border">Symbol</th>
                  <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border">Shares</th>
                  <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border">Price</th>
                  <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border">Total</th>
                  <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 bg-muted border-b border-border">Tax</th>
                </tr>
              </thead>
              <tbody>
                {currentTransactions.map((txn, idx) => (
                  <tr key={idx} className="border-b border-border/50 last:border-0 hover:bg-muted/50 transition-colors">
                    <td className="px-4 py-3.5 text-sm text-foreground">{txn.date}</td>
                    <td className="px-4 py-3.5">
                      <Badge variant={txn.action.toLowerCase() === 'buy' ? 'success' : 'info'} className="uppercase tracking-wide text-[0.6875rem] font-bold">
                        {txn.action}
                      </Badge>
                    </td>
                    <td className="px-4 py-3.5 font-mono font-bold text-sm text-foreground">{txn.symbol}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-sm text-foreground tabular-nums">{txn.shares.toFixed(4)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-sm text-foreground tabular-nums">{formatCurrency(txn.price)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-sm text-foreground tabular-nums">{formatCurrency(txn.total)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-sm text-foreground tabular-nums">
                      {txn.tax_paid !== null ? formatCurrency(txn.tax_paid) : '—'}
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
                Page {currentPage + 1} of {totalPages} ({history.transactions.length} total)
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
