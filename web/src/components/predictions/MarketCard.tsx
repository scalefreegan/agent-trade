import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { KalshiMarket } from '../../api/kalshi';

interface MarketCardProps {
  market: KalshiMarket;
}

export function MarketCard({ market }: MarketCardProps) {
  // Generate Kalshi URL: /markets/{event_ticker} (simple format)
  // Extract event ticker from market ticker if not available (e.g., "kxoaianth-40" -> "kxoaianth")
  let eventTicker = market.eventTicker || market.event_ticker || market.ticker || '';

  // Remove common market ticker suffixes to get base event ticker
  if (eventTicker) {
    eventTicker = eventTicker.toLowerCase().replace(/-\d+.*$/, '');
  }

  const kalshiUrl = eventTicker ? `https://kalshi.com/markets/${eventTicker}` : '#';

  // Convert cents to percentage
  const yesPrice = market.yes_bid ? (market.yes_bid / 100).toFixed(1) : '—';
  const noPrice = market.no_bid ? (market.no_bid / 100).toFixed(1) : '—';

  // Format close time
  const closeDate = new Date(market.close_time);
  const isClosingSoon = closeDate.getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000; // 7 days
  const closeDateStr = closeDate.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  // Format volume
  const formatVolume = (vol: number) => {
    if (vol >= 1_000_000) return `$${(vol / 1_000_000).toFixed(1)}M`;
    if (vol >= 1_000) return `$${(vol / 1_000).toFixed(1)}K`;
    return `$${vol}`;
  };

  // Status badge variant
  const statusVariant = market.status === 'open' ? 'success' : 'neutral';

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
              <div className="text-2xl font-bold text-gain">{yesPrice}¢</div>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">No</div>
              <div className="text-2xl font-bold text-loss">{noPrice}¢</div>
            </div>
          </div>

          {/* Metadata */}
          <div className="flex items-center justify-between text-sm text-muted-foreground border-t border-border pt-3">
            <div className="flex items-center gap-3">
              <div>
                <span className="font-medium text-foreground">
                  {formatVolume(market.volume_24h)}
                </span>
                <span className="ml-1">24h vol</span>
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
