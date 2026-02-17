import type { ExperimentReport } from '../../api/analysis';
import { Card } from '../ui/Card';
import { Badge, statusVariant } from '../ui/Badge';

interface ExperimentReportViewProps {
  report: ExperimentReport;
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);

const formatPct = (value: number) => `${value.toFixed(2)}%`;

export function ExperimentReportView({ report }: ExperimentReportViewProps) {
  if (!report.leaderboard) {
    return (
      <div className="flex items-center justify-center h-32 bg-muted rounded-lg">
        <div className="text-muted-foreground">Report data unavailable</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary card */}
      <Card>
        <h3 className="text-xl font-semibold text-foreground mb-4">Experiment Report</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Status</p>
            <p className="mt-1 font-medium text-foreground capitalize">{report.status}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Trading Day</p>
            <p className="mt-1 font-medium text-foreground">{report.trading_day}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Active Agents</p>
            <p className="mt-1 font-medium text-foreground">
              {report.num_agents_active} / {report.num_agents_total}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Last Run</p>
            <p className="mt-1 font-medium text-foreground">
              {report.last_run ? new Date(report.last_run).toLocaleDateString() : 'Never'}
            </p>
          </div>
        </div>
      </Card>

      {/* Leaderboard */}
      <Card>
        <h4 className="text-lg font-semibold text-foreground mb-4">Leaderboard</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 pr-4 font-medium text-muted-foreground">Rank</th>
                <th className="text-left py-2 pr-4 font-medium text-muted-foreground">Agent</th>
                <th className="text-right py-2 pr-4 font-medium text-muted-foreground">Portfolio Value</th>
                <th className="text-left py-2 font-medium text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {report.leaderboard.map((entry) => (
                <tr key={entry.agent_id} className="hover:bg-muted/50 transition-colors">
                  <td className="py-3 pr-4 text-muted-foreground font-mono">#{entry.rank}</td>
                  <td className="py-3 pr-4 font-medium text-foreground">{entry.name}</td>
                  <td className="py-3 pr-4 text-right font-medium text-foreground tabular-nums">
                    {formatCurrency(entry.portfolio_value)}
                  </td>
                  <td className="py-3">
                    <Badge variant={statusVariant(entry.status)}>
                      {entry.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Holding period distribution (if present) */}
      {report.holding_period_distribution && Object.keys(report.holding_period_distribution).length > 0 && (
        <Card>
          <h4 className="text-lg font-semibold text-foreground mb-4">Holding Period Distribution</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 pr-4 font-medium text-muted-foreground">Agent</th>
                  <th className="text-right py-2 pr-4 font-medium text-muted-foreground">0–30d</th>
                  <th className="text-right py-2 pr-4 font-medium text-muted-foreground">31–90d</th>
                  <th className="text-right py-2 pr-4 font-medium text-muted-foreground">91–180d</th>
                  <th className="text-right py-2 pr-4 font-medium text-muted-foreground">181–365d</th>
                  <th className="text-right py-2 font-medium text-gain">365+d ★</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {Object.entries(report.holding_period_distribution).map(([agentId, dist]) => {
                  const leaderboardEntry = report.leaderboard.find((e) => e.agent_id === agentId);
                  const agentName = leaderboardEntry?.name ?? agentId;
                  return (
                    <tr key={agentId} className="hover:bg-muted/50 transition-colors">
                      <td className="py-3 pr-4 font-medium text-foreground">{agentName}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-loss">{dist['0-30']}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-warning">{dist['31-90']}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-muted-foreground">{dist['91-180']}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-muted-foreground">{dist['181-365']}</td>
                      <td className="py-3 text-right tabular-nums font-medium text-gain">{dist['365+']}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">★ 365+ days qualifies for long-term capital gains rate</p>
        </Card>
      )}

      {/* Tax metrics summary (if present) */}
      {report.tax_metrics && Object.keys(report.tax_metrics).length > 0 && (
        <Card>
          <h4 className="text-lg font-semibold text-foreground mb-4">Tax Efficiency Summary</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 pr-4 font-medium text-muted-foreground">Agent</th>
                  <th className="text-right py-2 pr-4 font-medium text-muted-foreground">Total Tax</th>
                  <th className="text-right py-2 pr-4 font-medium text-muted-foreground">Short-term</th>
                  <th className="text-right py-2 pr-4 font-medium text-muted-foreground">Long-term</th>
                  <th className="text-right py-2 pr-4 font-medium text-muted-foreground">Tax Drag</th>
                  <th className="text-right py-2 font-medium text-muted-foreground">Avg Hold</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {Object.entries(report.tax_metrics).map(([agentId, metrics]) => {
                  const leaderboardEntry = report.leaderboard.find((e) => e.agent_id === agentId);
                  const agentName = leaderboardEntry?.name ?? agentId;
                  return (
                    <tr key={agentId} className="hover:bg-muted/50 transition-colors">
                      <td className="py-3 pr-4 font-medium text-foreground">{agentName}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-foreground">
                        {formatCurrency(metrics.total_tax)}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-warning">
                        {formatCurrency(metrics.short_term_tax)}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-gain">
                        {formatCurrency(metrics.long_term_tax)}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-muted-foreground">
                        {formatPct(metrics.tax_drag_pct)}
                      </td>
                      <td className="py-3 text-right tabular-nums text-muted-foreground">
                        {metrics.avg_holding_period_days.toFixed(1)}d
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
