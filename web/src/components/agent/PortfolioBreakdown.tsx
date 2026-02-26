import React, { useState } from 'react';
import type { Portfolio, PortfolioMetrics } from '../../api/types';
import { Card } from '../ui/Card';
import { MetricCard } from '../ui/MetricCard';

interface PortfolioBreakdownProps {
  portfolio: Portfolio;
  metrics: PortfolioMetrics;
}

export function PortfolioBreakdown({ portfolio, metrics }: PortfolioBreakdownProps) {
  const [expandedPosition, setExpandedPosition] = useState<string | null>(null);

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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const calculateHoldingPeriod = (purchaseDate: string) => {
    const now = new Date();
    const purchase = new Date(purchaseDate);
    const days = Math.floor((now.getTime() - purchase.getTime()) / (1000 * 60 * 60 * 24));
    return days;
  };

  const positions = Object.values(portfolio.positions).filter(p => p.total_shares > 0);

  const gainColor = metrics.unrealized_gain >= 0 ? 'text-gain' : 'text-loss';

  return (
    <div>
      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <MetricCard label="Total Value" value={<span className="font-mono text-2xl font-semibold">{formatCurrency(metrics.total_value)}</span>} />
        </Card>
        <Card>
          <MetricCard
            label="Unrealized Gain"
            value={<span className={`font-mono text-2xl font-semibold ${gainColor}`}>{formatCurrency(metrics.unrealized_gain)}</span>}
            secondary={formatPercent(metrics.unrealized_gain_pct)}
          />
        </Card>
        <Card>
          <MetricCard
            label="Cash"
            value={<span className="font-mono text-2xl font-semibold">{formatCurrency(portfolio.cash)}</span>}
            secondary={`${metrics.cash_pct.toFixed(1)}% of portfolio`}
          />
        </Card>
        <Card>
          <MetricCard
            label="Invested"
            value={<span className="font-mono text-2xl font-semibold">{formatCurrency(metrics.total_value - portfolio.cash)}</span>}
            secondary={`${metrics.invested_pct.toFixed(1)}% of portfolio`}
          />
        </Card>
      </div>

      {/* Positions Header */}
      <div className="flex justify-between items-center mb-4 pb-3 border-b-2 border-primary">
        <div className="text-xs font-bold tracking-widest uppercase text-primary">Holdings</div>
        <div className="font-mono text-xs text-muted-foreground font-medium">
          {positions.length} position{positions.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Positions Table */}
      {positions.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <svg className="w-12 h-12 mx-auto mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          <div className="text-sm font-medium">No positions held</div>
        </div>
      ) : (
        <table className="w-full border-separate border-spacing-0 mb-4">
          <thead>
            <tr>
              <th className="text-left text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted rounded-tl-md">Symbol</th>
              <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted">Shares</th>
              <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted">Avg Cost</th>
              <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted">Current Price</th>
              <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted">Current Value</th>
              <th className="text-right text-xs font-semibold tracking-wide uppercase text-muted-foreground px-4 py-3 border-b border-border bg-muted rounded-tr-md">Gain/Loss</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => {
              const isExpanded = expandedPosition === position.symbol;
              const gainLoss = position.unrealized_gain || 0;
              const costBasis = position.current_value ? position.current_value - gainLoss : 0;
              const gainLossPct = costBasis !== 0 ? (gainLoss / costBasis) * 100 : 0;
              const glColor = gainLoss >= 0 ? 'text-gain' : 'text-loss';

              return (
                <React.Fragment key={position.symbol}>
                  <tr
                    className={`cursor-pointer transition-colors border-b border-border ${isExpanded ? 'bg-muted' : 'hover:bg-muted'}`}
                    onClick={() => setExpandedPosition(isExpanded ? null : position.symbol)}
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
                    <td className="px-4 py-4 text-right font-mono text-sm text-foreground tabular-nums">{position.total_shares.toFixed(4)}</td>
                    <td className="px-4 py-4 text-right font-mono text-sm text-foreground tabular-nums">{formatCurrency(position.total_cost_basis)}</td>
                    <td className="px-4 py-4 text-right font-mono text-sm text-foreground tabular-nums">
                      {position.current_price ? formatCurrency(position.current_price) : '—'}
                    </td>
                    <td className="px-4 py-4 text-right font-mono text-sm text-foreground tabular-nums">
                      {position.current_value ? formatCurrency(position.current_value) : '—'}
                    </td>
                    <td className={`px-4 py-4 text-right font-mono text-sm font-semibold tabular-nums ${glColor}`}>
                      {position.unrealized_gain !== null ? (
                        <>
                          {formatCurrency(gainLoss)}
                          <div className="text-xs mt-0.5">{formatPercent(gainLossPct)}</div>
                        </>
                      ) : '—'}
                    </td>
                  </tr>

                  {/* Tax Lots Expandable */}
                  {isExpanded && (
                    <tr className="border-b border-border bg-gradient-to-b from-muted to-card">
                      <td colSpan={6}>
                        <div className="px-4 pl-12 py-6 animate-slide-down">
                          <div className="flex items-center gap-2 mb-3 text-xs font-semibold tracking-widest uppercase text-brand-800">
                            Tax Lots
                            <span className="bg-primary text-primary-foreground px-2 py-0.5 rounded-full text-[0.625rem] font-semibold">
                              {position.lots.length}
                            </span>
                          </div>
                          <table className="w-full border border-border rounded-md overflow-hidden">
                            <thead>
                              <tr>
                                <th className="text-left text-[0.625rem] font-semibold tracking-wide uppercase text-muted-foreground px-4 py-2.5 bg-card border-b border-border">Shares</th>
                                <th className="text-left text-[0.625rem] font-semibold tracking-wide uppercase text-muted-foreground px-4 py-2.5 bg-card border-b border-border">Cost Basis</th>
                                <th className="text-left text-[0.625rem] font-semibold tracking-wide uppercase text-muted-foreground px-4 py-2.5 bg-card border-b border-border">Purchase Date</th>
                                <th className="text-left text-[0.625rem] font-semibold tracking-wide uppercase text-muted-foreground px-4 py-2.5 bg-card border-b border-border">Holding Period</th>
                              </tr>
                            </thead>
                            <tbody>
                              {position.lots.map((lot, idx) => {
                                const holdingDays = calculateHoldingPeriod(lot.purchase_date);
                                const isLongTerm = holdingDays >= 365;
                                return (
                                  <tr key={idx} className="border-b border-border/50 last:border-0 hover:bg-muted/50">
                                    <td className="px-4 py-3 font-mono text-[0.8125rem] text-foreground">{lot.shares.toFixed(4)}</td>
                                    <td className="px-4 py-3 font-mono text-[0.8125rem] text-foreground">{formatCurrency(lot.cost_basis)}</td>
                                    <td className="px-4 py-3 font-mono text-[0.8125rem] text-foreground">{formatDate(lot.purchase_date)}</td>
                                    <td className="px-4 py-3">
                                      <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold font-mono ${isLongTerm ? 'bg-gain/15 text-gain' : 'bg-warning/15 text-warning'}`}>
                                        {holdingDays} day{holdingDays !== 1 ? 's' : ''}
                                      </span>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}

            {/* Cash Row */}
            <tr className="border-b-2 border-border bg-primary/[0.02]">
              <td className="px-4 py-4 font-semibold">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 opacity-0" fill="none" viewBox="0 0 24 24">
                    <path d="M9 5l7 7-7 7" />
                  </svg>
                  <span className="font-mono font-bold text-[0.9375rem] text-foreground">CASH</span>
                </div>
              </td>
              <td className="px-4 py-4 text-right font-mono text-sm text-foreground">—</td>
              <td className="px-4 py-4 text-right font-mono text-sm text-foreground">—</td>
              <td className="px-4 py-4 text-right font-mono text-sm text-foreground">—</td>
              <td className="px-4 py-4 text-right font-mono text-sm font-semibold text-foreground">{formatCurrency(portfolio.cash)}</td>
              <td className="px-4 py-4 text-right font-mono text-sm text-foreground">—</td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}
