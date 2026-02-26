import React, { useMemo, useState } from 'react';
import type { Portfolio, TransactionHistory } from '../../api/types';
import { Card } from '../ui/Card';
import { MetricCard } from '../ui/MetricCard';

interface ClosedPositionsProps {
  portfolio: Portfolio;
  transactions?: TransactionHistory;
}

export function ClosedPositions({ portfolio, transactions }: ClosedPositionsProps) {
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // Closed positions = positions with zero shares
  const closedPositions = Object.values(portfolio.positions).filter(
    (p) => p.total_shares === 0
  );

  // Build per-symbol aggregates from transactions
  const { buysBySymbol, sellsBySymbol } = useMemo(() => {
    const buys: Record<string, { totalCost: number; totalShares: number }> = {};
    const sells: Record<string, { totalProceeds: number; totalTax: number; sellCount: number }> = {};

    if (!transactions) return { buysBySymbol: buys, sellsBySymbol: sells };

    for (const txn of transactions.transactions) {
      if (txn.action === 'BUY') {
        if (!buys[txn.symbol]) buys[txn.symbol] = { totalCost: 0, totalShares: 0 };
        buys[txn.symbol].totalCost += txn.total;
        buys[txn.symbol].totalShares += txn.shares;
      } else if (txn.action === 'SELL') {
        if (!sells[txn.symbol]) sells[txn.symbol] = { totalProceeds: 0, totalTax: 0, sellCount: 0 };
        sells[txn.symbol].totalProceeds += txn.total;
        sells[txn.symbol].totalTax += txn.tax_paid ?? 0;
        sells[txn.symbol].sellCount += 1;
      }
    }

    return { buysBySymbol: buys, sellsBySymbol: sells };
  }, [transactions]);

  // Compute per-position metrics
  const positionMetrics = useMemo(() => {
    return closedPositions.map((position) => {
      const buys = buysBySymbol[position.symbol];
      const sells = sellsBySymbol[position.symbol];
      const totalInvested = buys?.totalCost ?? position.total_cost_basis;
      const totalProceeds = sells?.totalProceeds ?? 0;
      const totalTax = sells?.totalTax ?? 0;
      const realizedGain = totalProceeds - totalInvested - totalTax;
      const returnPct = totalInvested > 0 ? ((totalProceeds - totalInvested) / totalInvested) * 100 : 0;

      return { position, totalInvested, totalProceeds, totalTax, realizedGain, returnPct };
    });
  }, [closedPositions, buysBySymbol, sellsBySymbol]);

  // Summary metrics
  const summary = useMemo(() => {
    let totalInvested = 0;
    let totalProceeds = 0;
    let totalTaxPaid = 0;
    let totalRealizedGain = 0;
    let winners = 0;

    for (const m of positionMetrics) {
      totalInvested += m.totalInvested;
      totalProceeds += m.totalProceeds;
      totalTaxPaid += m.totalTax;
      totalRealizedGain += m.realizedGain;
      if (m.realizedGain >= 0) winners++;
    }

    const winRate = positionMetrics.length > 0 ? (winners / positionMetrics.length) * 100 : 0;

    return { totalInvested, totalProceeds, totalTaxPaid, totalRealizedGain, winRate };
  }, [positionMetrics]);

  // Get all transactions for a symbol (for the expanded detail view)
  const getSymbolTransactions = (symbol: string) => {
    if (!transactions) return [];
    return transactions.transactions
      .filter((t) => t.symbol === symbol)
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  };

  if (closedPositions.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <svg className="w-12 h-12 mx-auto mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div className="text-sm font-medium">No closed positions yet</div>
        <div className="text-xs mt-1">Positions will appear here after they are fully sold</div>
      </div>
    );
  }

  const gainColor = summary.totalRealizedGain >= 0 ? 'text-gain' : 'text-loss';

  return (
    <div>
      {/* Summary Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <MetricCard
            label="Realized Gain/Loss"
            value={<span className={`font-mono text-xl font-semibold ${gainColor}`}>{formatCurrency(summary.totalRealizedGain)}</span>}
          />
        </Card>
        <Card>
          <MetricCard
            label="Total Invested"
            value={<span className="font-mono text-xl font-semibold">{formatCurrency(summary.totalInvested)}</span>}
          />
        </Card>
        <Card>
          <MetricCard
            label="Total Tax Paid"
            value={<span className="font-mono text-xl font-semibold">{formatCurrency(summary.totalTaxPaid)}</span>}
          />
        </Card>
        <Card>
          <MetricCard
            label="Win Rate"
            value={<span className="font-mono text-xl font-semibold">{summary.winRate.toFixed(0)}%</span>}
            secondary={`${positionMetrics.length} closed position${positionMetrics.length !== 1 ? 's' : ''}`}
          />
        </Card>
      </div>

      {/* Header */}
      <div className="flex justify-between items-center mb-4 pb-3 border-b-2 border-primary">
        <div className="text-xs font-bold tracking-widest uppercase text-primary">
          Closed Positions
        </div>
        <div className="font-mono text-xs text-muted-foreground font-medium">
          {closedPositions.length} position{closedPositions.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Table */}
      <table className="w-full border-separate border-spacing-0 mb-4">
        <thead>
          <tr>
            <th className="text-left text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted rounded-tl-md">Symbol</th>
            <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted">Total Invested</th>
            <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted">Total Proceeds</th>
            <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted">Tax Paid</th>
            <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted">Return</th>
            <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted rounded-tr-md">Realized Gain</th>
          </tr>
        </thead>
        <tbody>
          {positionMetrics.map(({ position, totalInvested, totalProceeds, totalTax, realizedGain, returnPct }) => {
            const isExpanded = expandedSymbol === position.symbol;
            const glColor = realizedGain >= 0 ? 'text-gain' : 'text-loss';

            return (
              <React.Fragment key={position.symbol}>
                <tr
                  className={`cursor-pointer transition-colors border-b border-border ${isExpanded ? 'bg-muted' : 'hover:bg-muted'}`}
                  onClick={() => setExpandedSymbol(isExpanded ? null : position.symbol)}
                >
                  <td className="px-4 py-4 text-sm">
                    <div className="flex items-center gap-2">
                      <svg
                        className={`w-4 h-4 text-muted-foreground flex-shrink-0 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      <span className="font-mono font-bold text-[0.9375rem] text-foreground">{position.symbol}</span>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-right font-mono text-sm text-foreground tabular-nums">
                    {formatCurrency(totalInvested)}
                  </td>
                  <td className="px-4 py-4 text-right font-mono text-sm text-foreground tabular-nums">
                    {formatCurrency(totalProceeds)}
                  </td>
                  <td className="px-4 py-4 text-right font-mono text-sm text-foreground tabular-nums">
                    {formatCurrency(totalTax)}
                  </td>
                  <td className={`px-4 py-4 text-right font-mono text-sm tabular-nums ${glColor}`}>
                    {formatPercent(returnPct)}
                  </td>
                  <td className={`px-4 py-4 text-right font-mono text-sm font-semibold tabular-nums ${glColor}`}>
                    {formatCurrency(realizedGain)}
                  </td>
                </tr>

                {/* Transaction History Expandable */}
                {isExpanded && (
                  <tr className="border-b border-border bg-gradient-to-b from-muted to-card">
                    <td colSpan={6}>
                      <div className="px-4 pl-12 py-6 animate-slide-down">
                        <div className="flex items-center gap-2 mb-3 text-xs font-semibold tracking-widest uppercase text-brand-800">
                          Trade History
                          <span className="bg-primary text-primary-foreground px-2 py-0.5 rounded-full text-[0.625rem] font-semibold">
                            {getSymbolTransactions(position.symbol).length}
                          </span>
                        </div>
                        <table className="w-full border border-border rounded-md overflow-hidden">
                          <thead>
                            <tr>
                              <th className="text-left text-[0.625rem] font-semibold tracking-wide uppercase text-muted-foreground px-4 py-2.5 bg-card border-b border-border">Date</th>
                              <th className="text-left text-[0.625rem] font-semibold tracking-wide uppercase text-muted-foreground px-4 py-2.5 bg-card border-b border-border">Action</th>
                              <th className="text-right text-[0.625rem] font-semibold tracking-wide uppercase text-muted-foreground px-4 py-2.5 bg-card border-b border-border">Shares</th>
                              <th className="text-right text-[0.625rem] font-semibold tracking-wide uppercase text-muted-foreground px-4 py-2.5 bg-card border-b border-border">Price</th>
                              <th className="text-right text-[0.625rem] font-semibold tracking-wide uppercase text-muted-foreground px-4 py-2.5 bg-card border-b border-border">Total</th>
                              <th className="text-right text-[0.625rem] font-semibold tracking-wide uppercase text-muted-foreground px-4 py-2.5 bg-card border-b border-border">Tax</th>
                            </tr>
                          </thead>
                          <tbody>
                            {getSymbolTransactions(position.symbol).map((txn, idx) => (
                              <tr key={idx} className="border-b border-border/50 last:border-0 hover:bg-muted/50">
                                <td className="px-4 py-3 font-mono text-[0.8125rem] text-foreground">{txn.date}</td>
                                <td className="px-4 py-3">
                                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[0.625rem] font-bold ${
                                    txn.action === 'BUY' ? 'bg-gain/15 text-gain' : 'bg-primary/15 text-primary'
                                  }`}>
                                    {txn.action}
                                  </span>
                                </td>
                                <td className="px-4 py-3 font-mono text-[0.8125rem] text-foreground text-right">{txn.shares.toFixed(4)}</td>
                                <td className="px-4 py-3 font-mono text-[0.8125rem] text-foreground text-right">{formatCurrency(txn.price)}</td>
                                <td className="px-4 py-3 font-mono text-[0.8125rem] text-foreground text-right">{formatCurrency(txn.total)}</td>
                                <td className="px-4 py-3 font-mono text-[0.8125rem] text-foreground text-right">
                                  {txn.tax_paid !== null ? formatCurrency(txn.tax_paid) : '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
