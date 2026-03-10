import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { KalshiMarket } from '../../api/kalshi';

interface MarketCardProps {
  market: KalshiMarket;
}

export function MarketCard({ market }: MarketCardProps) {
  // Use event_ticker directly for Kalshi URL
  const eventTicker = market.event_ticker || '';
  const kalshiUrl = eventTicker ? `https://kalshi.com/markets/${eventTicker.toLowerCase()}` : '#';

  // Kalshi returns prices in cents (1-99), display as percentage
  const yesPrice = market.yes_bid ? `${market.yes_bid}` : '—';
  const noPrice = market.no_bid ? `${market.no_bid}` : '—';

  // Format close time with validation
  const closeDate = new Date(market.close_time);
  const isValidDate = !isNaN(closeDate.getTime());
  const isClosingSoon = isValidDate && closeDate.getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000; // 7 days
  const closeDateStr = isValidDate
    ? closeDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : '—';

  // Format volume with validation
  const formatVolume = (vol: number | undefined | null) => {
    if (vol == null || isNaN(vol)) return '—';
    if (vol >= 1_000_000) return `$${(vol / 1_000_000).toFixed(1)}M`;
    if (vol >= 1_000) return `$${(vol / 1_000).toFixed(1)}K`;
    return `$${vol}`;
  };

  // Status badge variant
  const statusVariant =
    market.status === 'open' ? 'success' :
    market.status === 'settled' ? 'warning' :
    'neutral';

  return (
    <a
      href={kalshiUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="block"
    >
      <Card className="hover:border-primary transition-colors cursor-pointer">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-base font-semibold text-foreground line-clamp-2 flex-1">
              {market.title}
            </h3>
            <Badge variant={statusVariant}>
              {market.status}
            </Badge>
          </div>

          {/* Subtitle if available */}
          {market.subtitle && (
            <p className="text-sm text-muted-foreground line-clamp-1">
              {market.subtitle}
            </p>
          )}

          {/* Prices */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Yes</div>
              <div className="text-2xl font-bold text-gain">{yesPrice}%</div>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">No</div>
              <div className="text-2xl font-bold text-loss">{noPrice}%</div>
            </div>
          </div>

          {/* Metadata */}
          <div className="flex items-center justify-between text-sm text-muted-foreground border-t border-border pt-3">
            <div className="flex items-center gap-3">
              <div>
                <span className="font-medium text-foreground">
                  {formatVolume(market.volume)}
                </span>
                <span className="ml-1">vol</span>
              </div>
              <div className="w-px h-4 bg-border" />
              <div>
                <span className="font-medium text-foreground">
                  {formatVolume(market.volume_24h)}
                </span>
                <span className="ml-1">24h</span>
              </div>
              <div className="w-px h-4 bg-border" />
              <div>
                <span className="font-medium text-foreground">
                  {formatVolume(market.open_interest)}
                </span>
                <span className="ml-1">OI</span>
              </div>
            </div>
            <div className={isClosingSoon ? 'text-warning font-medium' : ''}>
              Closes {closeDateStr}
            </div>
          </div>
        </div>
      </Card>
    </a>
  );
}
