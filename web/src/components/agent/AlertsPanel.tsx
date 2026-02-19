import type { AlertsResponse } from '../../api/types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';

interface AlertsPanelProps {
  data: AlertsResponse;
}

export function AlertsPanel({ data }: AlertsPanelProps) {
  if (data.alerts.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <svg className="w-12 h-12 mx-auto mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        <div className="text-sm font-medium mb-1">No alerts flagged</div>
        <div className="text-xs">Agents only flag rare, high-conviction opportunities.</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-6 pb-3 border-b-2 border-primary">
        <div className="text-xs font-bold tracking-widest uppercase text-primary">High-Conviction Alerts</div>
        <span className="text-xs font-mono text-muted-foreground">
          {data.total_count} alert{data.total_count !== 1 ? 's' : ''}
        </span>
      </div>

      {data.alerts.map((alert, idx) => (
        <Card key={idx}>
          <div className="flex items-start justify-between gap-4 mb-3">
            <div className="flex items-center gap-3">
              <span className="font-mono font-bold text-lg text-foreground">{alert.symbol}</span>
              <Badge variant={alert.confidence === 'very_high' ? 'error' : 'warning'}>
                {alert.confidence === 'very_high' ? 'Very High' : 'High'} Conviction
              </Badge>
            </div>
            <span className="font-mono text-xs text-muted-foreground bg-muted px-2 py-1 rounded flex-shrink-0">
              {alert.date}
            </span>
          </div>

          <p className="text-sm text-foreground leading-relaxed mb-3">{alert.thesis}</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-border">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">Catalyst</div>
              <div className="text-sm text-foreground">{alert.catalyst}</div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">Time Horizon</div>
              <div className="text-sm text-foreground">{alert.time_horizon}</div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
