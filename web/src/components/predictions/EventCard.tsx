import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { KalshiEvent, KalshiMarket } from '../../api/kalshi';

interface EventCardProps {
  event: KalshiEvent;
}

function formatVolume(vol: number | undefined | null) {
  if (vol == null || isNaN(vol)) return '—';
  if (vol >= 1_000_000) return `$${(vol / 1_000_000).toFixed(1)}M`;
  if (vol >= 1_000) return `$${(vol / 1_000).toFixed(1)}K`;
  return `$${vol}`;
}

export function EventCard({ event }: EventCardProps) {
  const markets = event.markets ?? [];
  const isSingleMarket = markets.length === 1;
  const kalshiUrl = `https://kalshi.com/markets/${event.event_ticker}`;

  // Aggregate metrics across all markets in the event
  const totalVolume = markets.reduce((sum, m) => sum + (m.volume || 0), 0);
  const totalVolume24h = markets.reduce((sum, m) => sum + (m.volume_24h || 0), 0);
  const totalOI = markets.reduce((sum, m) => sum + (m.open_interest || 0), 0);

  // Earliest close time across markets
  const earliestClose = markets.reduce<Date | null>((earliest, m) => {
    const d = new Date(m.close_time);
    if (isNaN(d.getTime())) return earliest;
    return earliest === null || d < earliest ? d : earliest;
  }, null);

  const closeDateStr = earliestClose
    ? earliestClose.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '—';
  const isClosingSoon = earliestClose
    ? earliestClose.getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000
    : false;

  return (
    <a href={kalshiUrl} target="_blank" rel="noopener noreferrer" className="block">
      <Card className="hover:border-primary transition-colors cursor-pointer">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-base font-semibold text-foreground line-clamp-2 flex-1">
              {event.title}
            </h3>
            <Badge variant="info">{event.category}</Badge>
          </div>

          {/* Subtitle */}
          {event.sub_title && (
            <p className="text-sm text-muted-foreground line-clamp-1">{event.sub_title}</p>
          )}

          {/* Content: single-market vs multi-market */}
          {isSingleMarket ? (
            <SingleMarketDisplay market={markets[0]} />
          ) : (
            <MultiMarketDisplay markets={markets} />
          )}

          {/* Footer */}
          <div className="flex items-center justify-between text-sm text-muted-foreground border-t border-border pt-3">
            <div className="flex items-center gap-3">
              <div>
                <span className="font-medium text-foreground">{formatVolume(totalVolume)}</span>
                <span className="ml-1">vol</span>
              </div>
              <div className="w-px h-4 bg-border" />
              <div>
                <span className="font-medium text-foreground">{formatVolume(totalVolume24h)}</span>
                <span className="ml-1">24h</span>
              </div>
              <div className="w-px h-4 bg-border" />
              <div>
                <span className="font-medium text-foreground">{formatVolume(totalOI)}</span>
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

function SingleMarketDisplay({ market }: { market: KalshiMarket }) {
  const yesPrice = market.yes_bid ? `${market.yes_bid}` : '—';
  const noPrice = market.no_bid ? `${market.no_bid}` : '—';

  return (
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
  );
}

function MultiMarketDisplay({ markets }: { markets: KalshiMarket[] }) {
  const MAX_OPTIONS = 6;
  const sorted = [...markets].sort((a, b) => (b.yes_bid || 0) - (a.yes_bid || 0));
  const topOptions = sorted.slice(0, MAX_OPTIONS);
  const remaining = sorted.length - MAX_OPTIONS;

  return (
    <div className="space-y-1.5">
      {topOptions.map((m) => {
        const label = m.yes_sub_title || m.title;
        const pct = m.yes_bid || 0;
        return (
          <div key={m.ticker} className="flex items-center gap-2">
            <span className="text-sm text-foreground truncate flex-1">{label}</span>
            <div className="flex items-center gap-2 shrink-0">
              <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full"
                  style={{ width: `${Math.min(pct, 100)}%` }}
                />
              </div>
              <span className="text-sm font-medium text-foreground w-10 text-right">{pct}%</span>
            </div>
          </div>
        );
      })}
      {remaining > 0 && (
        <div className="text-xs text-muted-foreground">+{remaining} more</div>
      )}
    </div>
  );
}
