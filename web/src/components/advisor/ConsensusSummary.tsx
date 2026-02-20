import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';
import type { AdvisorRecommendation } from '../../api/types';

interface ConsensusSummaryProps {
  recommendations: AdvisorRecommendation[];
  symbol: string;
}

export function ConsensusSummary({ recommendations, symbol }: ConsensusSummaryProps) {
  if (recommendations.length === 0) return null;

  const buyCount = recommendations.filter((r) => r.action === 'BUY').length;
  const sellCount = recommendations.filter((r) => r.action === 'SELL').length;
  const holdCount = recommendations.filter((r) => r.action === 'HOLD').length;

  const targetPrices = recommendations
    .map((r) => r.target_price)
    .filter((p): p is number => p != null);
  const avgTarget = targetPrices.length > 0
    ? targetPrices.reduce((a, b) => a + b, 0) / targetPrices.length
    : null;

  const avgConfidence =
    recommendations.reduce((sum, r) => sum + r.confidence, 0) / recommendations.length;

  // Collect all risk factors, count frequency
  const riskCounts = new Map<string, number>();
  for (const rec of recommendations) {
    for (const risk of rec.risk_factors) {
      const normalized = risk.toLowerCase();
      riskCounts.set(normalized, (riskCounts.get(normalized) ?? 0) + 1);
    }
  }
  const commonRisks = [...riskCounts.entries()]
    .filter(([, count]) => count >= 2)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([risk]) => risk);

  // Determine consensus
  const maxVotes = Math.max(buyCount, sellCount, holdCount);
  let consensus: string;
  if (buyCount === maxVotes && buyCount > sellCount && buyCount > holdCount) {
    consensus = 'BUY';
  } else if (sellCount === maxVotes && sellCount > buyCount && sellCount > holdCount) {
    consensus = 'SELL';
  } else if (holdCount === maxVotes && holdCount > buyCount && holdCount > sellCount) {
    consensus = 'HOLD';
  } else {
    consensus = 'MIXED';
  }

  const consensusVariant =
    consensus === 'BUY' ? 'success'
    : consensus === 'SELL' ? 'error'
    : consensus === 'HOLD' ? 'neutral'
    : 'warning';

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-foreground">Consensus for {symbol}</h3>
        <Badge variant={consensusVariant}>{consensus}</Badge>
      </div>

      {/* Vote tally */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <VotePill label="Buy" count={buyCount} total={recommendations.length} color="bg-gain" />
        <VotePill label="Hold" count={holdCount} total={recommendations.length} color="bg-muted-foreground" />
        <VotePill label="Sell" count={sellCount} total={recommendations.length} color="bg-loss" />
      </div>

      {/* Summary metrics */}
      <div className="grid grid-cols-2 gap-4 text-center py-3 border-t border-border">
        <div>
          <p className="text-xs text-muted-foreground">Avg Confidence</p>
          <p className="text-lg font-medium text-foreground">{Math.round(avgConfidence * 100)}%</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Avg Target</p>
          <p className="text-lg font-medium text-foreground">
            {avgTarget != null
              ? `$${avgTarget.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : '—'}
          </p>
        </div>
      </div>

      {/* Common risks */}
      {commonRisks.length > 0 && (
        <div className="pt-3 border-t border-border">
          <p className="text-xs font-medium text-muted-foreground mb-2">Common Risk Factors</p>
          <ul className="space-y-1">
            {commonRisks.map((risk, i) => (
              <li key={i} className="text-xs text-muted-foreground flex gap-1.5">
                <span className="text-loss shrink-0">!</span>
                <span className="capitalize">{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

function VotePill({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;

  return (
    <div className="flex flex-col items-center gap-1.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-medium text-foreground">{count}</p>
      <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
