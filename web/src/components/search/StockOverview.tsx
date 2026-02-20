import type { StockInfo } from '../../api/types';
import { Card } from '../ui/Card';
import { MetricCard } from '../ui/MetricCard';
import { Badge } from '../ui/Badge';

interface StockOverviewProps {
  stock: StockInfo;
}

function formatNumber(n: number | null): string {
  if (n == null) return '--';
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatMarketCap(n: number | null): string {
  if (n == null) return '--';
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString()}`;
}

function formatVolume(n: number | null): string {
  if (n == null) return '--';
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toLocaleString();
}

export function StockOverview({ stock }: StockOverviewProps) {
  const priceRange =
    stock.fifty_two_week_low != null && stock.fifty_two_week_high != null
      ? `$${formatNumber(stock.fifty_two_week_low)} - $${formatNumber(stock.fifty_two_week_high)}`
      : '--';

  return (
    <Card>
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-foreground">{stock.symbol}</h2>
          {stock.name && (
            <p className="text-sm text-muted-foreground mt-0.5">{stock.name}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {stock.sector && <Badge variant="info">{stock.sector}</Badge>}
          {stock.industry && <Badge variant="neutral">{stock.industry}</Badge>}
        </div>
      </div>

      {stock.current_price != null && (
        <p className="text-3xl font-bold text-foreground mb-6">
          ${formatNumber(stock.current_price)}
        </p>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Market Cap" value={formatMarketCap(stock.market_cap)} />
        <MetricCard label="P/E Ratio" value={stock.pe_ratio != null ? formatNumber(stock.pe_ratio) : '--'} />
        <MetricCard label="Volume" value={formatVolume(stock.volume)} secondary={stock.average_volume ? `Avg: ${formatVolume(stock.average_volume)}` : undefined} />
        <MetricCard label="52-Week Range" value={priceRange} />
      </div>

      {stock.business_summary && (
        <p className="mt-4 text-sm text-muted-foreground leading-relaxed line-clamp-3">
          {stock.business_summary}
        </p>
      )}
    </Card>
  );
}
