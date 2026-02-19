import { useState } from 'react';
import type { HoldingsInfo as HoldingsInfoType } from '../../api/types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';

interface HoldingsInfoProps {
  data: HoldingsInfoType;
}

export function HoldingsInfo({ data }: HoldingsInfoProps) {
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(value);

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });

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

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-6 pb-3 border-b-2 border-primary">
        <div className="text-xs font-bold tracking-widest uppercase text-primary">Holdings Rationale</div>
        <span className="text-xs font-mono text-muted-foreground">
          {data.holdings.length} position{data.holdings.length !== 1 ? 's' : ''}
        </span>
      </div>

      {data.holdings.map((holding) => {
        const isExpanded = expandedSymbol === holding.symbol;
        const gainLoss = holding.unrealized_gain ?? 0;
        const gainColor = gainLoss >= 0 ? 'text-gain' : 'text-loss';

        return (
          <Card key={holding.symbol}>
            {/* Holding Header Row */}
            <div
              className="flex items-start justify-between cursor-pointer"
              onClick={() => setExpandedSymbol(isExpanded ? null : holding.symbol)}
            >
              <div className="flex items-center gap-3">
                <svg
                  className={`w-4 h-4 text-muted-foreground flex-shrink-0 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <div>
                  <span className="font-mono font-bold text-lg text-foreground">{holding.symbol}</span>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    First bought {formatDate(holding.first_buy_date)}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4 text-right">
                <div>
                  <div className="text-xs text-muted-foreground">Shares</div>
                  <div className="font-mono text-sm text-foreground tabular-nums">{holding.total_shares.toFixed(4)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Avg Cost</div>
                  <div className="font-mono text-sm text-foreground tabular-nums">{formatCurrency(holding.avg_cost_basis)}</div>
                </div>
                {holding.current_value !== null && (
                  <div>
                    <div className="text-xs text-muted-foreground">Value</div>
                    <div className="font-mono text-sm text-foreground tabular-nums">{formatCurrency(holding.current_value)}</div>
                  </div>
                )}
                {holding.unrealized_gain !== null && (
                  <Badge variant={gainLoss >= 0 ? 'success' : 'error'}>
                    <span className={`font-mono text-xs ${gainColor}`}>
                      {gainLoss >= 0 ? '+' : ''}{formatCurrency(gainLoss)}
                    </span>
                  </Badge>
                )}
              </div>
            </div>

            {/* Expandable Buy Rationale */}
            {isExpanded && (
              <div className="mt-4 pt-4 border-t border-border animate-slide-down">
                <div className="text-xs font-semibold tracking-widest uppercase text-primary mb-3">
                  Buy Rationale
                  <span className="ml-2 bg-primary text-primary-foreground px-2 py-0.5 rounded-full text-[0.625rem] font-semibold">
                    {holding.buy_reasons.length}
                  </span>
                </div>

                {holding.buy_reasons.length === 0 ? (
                  <div className="text-sm text-muted-foreground italic">No buy reasoning recorded.</div>
                ) : (
                  <div className="space-y-3">
                    {holding.buy_reasons.map((reason, idx) => (
                      <div key={idx} className="flex gap-3">
                        <div className="flex-shrink-0">
                          <span className="font-mono text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                            {reason.date}
                          </span>
                        </div>
                        <p className="text-sm text-foreground leading-relaxed">{reason.reasoning}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}
