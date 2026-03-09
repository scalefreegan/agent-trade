import { useState } from 'react';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';
import type { HoldingsInfo as HoldingsInfoType } from '../../api/types';
import { Card } from '../ui/Card';
import { useChartTheme } from '../../hooks/useChartTheme';
import { formatCurrency, formatDate, formatMarketCap } from '../../lib/format';

type PriceViewMode = 'price' | 'percent';

interface HoldingsInfoProps {
  data: HoldingsInfoType;
}

function toPercentChange(data: { date: string; close: number }[]) {
  if (data.length === 0) return [];
  const base = data[0].close;
  if (base === 0) return data.map((p) => ({ date: p.date, close: 0 }));
  return data.map((p) => ({
    date: p.date,
    close: ((p.close - base) / base) * 100,
  }));
}

function Sparkline({
  data,
  color,
  viewMode,
}: {
  data: { date: string; close: number }[];
  color: string;
  viewMode: PriceViewMode;
}) {
  const ct = useChartTheme();
  if (data.length < 2) return null;

  const chartData = viewMode === 'percent' ? toPercentChange(data) : data;

  return (
    <ResponsiveContainer width="100%" height={64}>
      <LineChart data={chartData} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
        <Tooltip
          contentStyle={{
            backgroundColor: ct.tooltip.bg,
            border: `1px solid ${ct.tooltip.border}`,
            borderRadius: '0.25rem',
            padding: '0.375rem 0.5rem',
            fontSize: '0.75rem',
            color: ct.tooltip.text,
          }}
          formatter={(v: number | undefined) => {
            const val = v ?? 0;
            return [
              viewMode === 'percent'
                ? `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`
                : formatCurrency(val),
              viewMode === 'percent' ? 'Change' : 'Close',
            ];
          }}
          labelFormatter={(label) => String(label)}
        />
        <Line
          type="monotone"
          dataKey="close"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          activeDot={{ r: 3, fill: color }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function HoldingsInfo({ data }: HoldingsInfoProps) {
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
  const [summaryExpanded, setSummaryExpanded] = useState<Set<string>>(new Set());
  const [priceView, setPriceView] = useState<PriceViewMode>('price');
  const ct = useChartTheme();

  const toggleSummary = (symbol: string) => {
    setSummaryExpanded(prev => {
      const next = new Set(prev);
      next.has(symbol) ? next.delete(symbol) : next.add(symbol);
      return next;
    });
  };

  if (data.holdings.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <svg className="w-12 h-12 mx-auto mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10" />
        </svg>
        <div className="text-sm font-medium">No positions held</div>
      </div>
    );
  }

  const toggleBtnClass = (active: boolean) =>
    `px-2 py-0.5 text-xs font-medium rounded-md transition-colors ${
      active
        ? 'bg-primary text-primary-foreground'
        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
    }`;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2 pb-3 border-b-2 border-primary">
        <div className="text-xs font-bold tracking-widest uppercase text-primary">Holdings</div>
        <span className="text-xs font-mono text-muted-foreground">
          {data.holdings.length} position{data.holdings.length !== 1 ? 's' : ''}
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">Sparklines</span>
          <div className="flex gap-0.5 bg-muted rounded-lg p-0.5">
            <button
              onClick={() => setPriceView('price')}
              className={toggleBtnClass(priceView === 'price')}
            >
              $
            </button>
            <button
              onClick={() => setPriceView('percent')}
              className={toggleBtnClass(priceView === 'percent')}
            >
              %
            </button>
          </div>
        </div>
      </div>

      {data.holdings.map((holding) => {
        const isExpanded = expandedSymbol === holding.symbol;
        const isSummaryExpanded = summaryExpanded.has(holding.symbol);
        const gainLoss = holding.unrealized_gain ?? 0;
        const gainColor = gainLoss >= 0 ? 'text-gain' : 'text-loss';

        // Sparkline trend color
        const sparkColor = holding.price_history.length >= 2
          ? (holding.price_history[holding.price_history.length - 1].close >= holding.price_history[0].close
            ? ct.gainColor : ct.lossColor)
          : ct.primaryColor;

        // 52-week position as percentage for range bar
        const rangeWidth = holding.fifty_two_week_high && holding.fifty_two_week_low && holding.current_price
          ? Math.max(0, Math.min(100, (
              (holding.current_price - holding.fifty_two_week_low) /
              (holding.fifty_two_week_high - holding.fifty_two_week_low) * 100
            )))
          : null;

        return (
          <Card key={holding.symbol}>
            {/* ── Header row ── */}
            <div className="flex items-start gap-4">
              {/* Symbol + company */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono font-bold text-xl text-foreground">{holding.symbol}</span>
                  {holding.company_name && (
                    <span className="text-sm text-muted-foreground truncate">{holding.company_name}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  {holding.sector && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                      {holding.sector}
                    </span>
                  )}
                  {holding.industry && holding.industry !== holding.sector && (
                    <span className="text-xs text-muted-foreground">{holding.industry}</span>
                  )}
                </div>
              </div>

              {/* P&L summary */}
              <div className="text-right flex-shrink-0">
                {holding.current_value !== null && (
                  <div className="font-mono font-bold text-lg text-foreground">
                    {formatCurrency(holding.current_value)}
                  </div>
                )}
                {holding.unrealized_gain !== null && (
                  <div className={`font-mono text-sm font-semibold ${gainColor}`}>
                    {gainLoss >= 0 ? '+' : ''}{formatCurrency(gainLoss)}
                  </div>
                )}
              </div>
            </div>

            {/* ── Key metrics row ── */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-border">
              <div>
                <div className="text-xs text-muted-foreground mb-0.5">Shares held</div>
                <div className="font-mono text-sm font-semibold text-foreground">{holding.total_shares.toFixed(4)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-0.5">Avg cost</div>
                <div className="font-mono text-sm font-semibold text-foreground">{formatCurrency(holding.avg_cost_basis)}</div>
              </div>
              {holding.market_cap !== null && (
                <div>
                  <div className="text-xs text-muted-foreground mb-0.5">Market cap</div>
                  <div className="font-mono text-sm font-semibold text-foreground">{formatMarketCap(holding.market_cap)}</div>
                </div>
              )}
              {holding.pe_ratio !== null && (
                <div>
                  <div className="text-xs text-muted-foreground mb-0.5">P/E ratio</div>
                  <div className="font-mono text-sm font-semibold text-foreground">{holding.pe_ratio.toFixed(1)}×</div>
                </div>
              )}
            </div>

            {/* ── 52-week range bar ── */}
            {holding.fifty_two_week_low !== null && holding.fifty_two_week_high !== null && (
              <div className="mt-3">
                <div className="flex justify-between text-xs text-muted-foreground mb-1">
                  <span>52-wk low {formatCurrency(holding.fifty_two_week_low)}</span>
                  <span>52-wk high {formatCurrency(holding.fifty_two_week_high)}</span>
                </div>
                <div className="relative h-1.5 bg-muted rounded-full overflow-visible">
                  <div className="absolute inset-0 rounded-full bg-gradient-to-r from-loss/40 via-muted-foreground/20 to-gain/40" />
                  {rangeWidth !== null && (
                    <div
                      className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-foreground border-2 border-card shadow"
                      style={{ left: `calc(${rangeWidth}% - 5px)` }}
                    />
                  )}
                </div>
              </div>
            )}

            {/* ── 90-day sparkline ── */}
            {holding.price_history.length >= 2 && (
              <div className="mt-4">
                <div className="text-xs text-muted-foreground mb-1">
                  {priceView === 'percent' ? '90-day change' : '90-day price'}
                </div>
                <Sparkline data={holding.price_history} color={sparkColor} viewMode={priceView} />
              </div>
            )}

            {/* ── Business summary ── */}
            {holding.business_summary && (
              <div className="mt-4 pt-4 border-t border-border">
                <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">About</div>
                <p className={`text-sm text-foreground leading-relaxed ${!isSummaryExpanded ? 'line-clamp-3' : ''}`}>
                  {holding.business_summary}
                </p>
                <button
                  onClick={() => toggleSummary(holding.symbol)}
                  className="mt-1 text-xs text-primary hover:underline focus:outline-none"
                >
                  {isSummaryExpanded ? 'Show less' : 'Show more'}
                </button>
              </div>
            )}

            {/* ── Buy rationale (expandable) ── */}
            <div className="mt-4 pt-4 border-t border-border">
              <button
                className="flex items-center gap-2 w-full text-left"
                onClick={() => setExpandedSymbol(isExpanded ? null : holding.symbol)}
              >
                <svg
                  className={`w-3.5 h-3.5 text-muted-foreground flex-shrink-0 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <span className="text-xs font-semibold uppercase tracking-widest text-primary">
                  Buy Rationale
                </span>
                <span className="ml-1 bg-primary text-primary-foreground px-1.5 py-0.5 rounded-full text-[0.625rem] font-semibold">
                  {holding.buy_reasons.length}
                </span>
                <span className="ml-auto text-xs text-muted-foreground">
                  First bought {formatDate(holding.first_buy_date)}
                </span>
              </button>

              {isExpanded && (
                <div className="mt-3 space-y-3 animate-slide-down">
                  {holding.buy_reasons.length === 0 ? (
                    <div className="text-sm text-muted-foreground italic">No buy reasoning recorded.</div>
                  ) : (
                    holding.buy_reasons.map((reason, idx) => (
                      <div key={idx} className="flex gap-3">
                        <span className="flex-shrink-0 font-mono text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                          {reason.date}
                        </span>
                        <p className="text-sm text-foreground leading-relaxed">{reason.reasoning}</p>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
