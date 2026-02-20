import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';
import type { AdvisorRecommendation } from '../../api/types';

interface RecommendationCardProps {
  recommendation: AdvisorRecommendation;
}

function actionVariant(action: string) {
  switch (action) {
    case 'BUY':
      return 'success' as const;
    case 'SELL':
      return 'error' as const;
    default:
      return 'neutral' as const;
  }
}

function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

function formatPrice(price: number | null): string {
  if (price == null) return '—';
  return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function RecommendationCard({ recommendation: rec }: RecommendationCardProps) {
  return (
    <Card className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground truncate">{rec.agent_name}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{rec.time_horizon}</p>
        </div>
        <Badge variant={actionVariant(rec.action)} className="shrink-0">
          {rec.action}
        </Badge>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-3 gap-3 text-center">
        <div>
          <p className="text-xs text-muted-foreground">Confidence</p>
          <p className="text-sm font-medium text-foreground">{formatConfidence(rec.confidence)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Current</p>
          <p className="text-sm font-medium text-foreground">{formatPrice(rec.current_price)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Target</p>
          <p className="text-sm font-medium text-foreground">{formatPrice(rec.target_price)}</p>
        </div>
      </div>

      {/* Amount guidance */}
      {rec.amount_guidance && (
        <p className="text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Sizing: </span>
          {rec.amount_guidance}
        </p>
      )}

      {/* Reasoning */}
      <p className="text-sm text-foreground leading-relaxed">{rec.reasoning}</p>

      {/* Risk factors */}
      {rec.risk_factors.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Risk Factors</p>
          <ul className="space-y-0.5">
            {rec.risk_factors.map((risk, i) => (
              <li key={i} className="text-xs text-muted-foreground flex gap-1.5">
                <span className="text-loss shrink-0">!</span>
                {risk}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
