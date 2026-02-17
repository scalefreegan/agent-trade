import type { ExperimentReport } from '../../api/analysis';

interface ExperimentReportViewProps {
  report: ExperimentReport;
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);

const formatPct = (value: number) => `${value.toFixed(2)}%`;

export function ExperimentReportView({ report }: ExperimentReportViewProps) {
  return (
    <div className="space-y-6">
      {/* Summary card */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">Experiment Report</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Status</p>
            <p className="mt-1 font-medium text-gray-900 capitalize">{report.status}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Trading Day</p>
            <p className="mt-1 font-medium text-gray-900">{report.trading_day}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Active Agents</p>
            <p className="mt-1 font-medium text-gray-900">
              {report.num_agents_active} / {report.num_agents_total}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Last Run</p>
            <p className="mt-1 font-medium text-gray-900">
              {report.last_run ? new Date(report.last_run).toLocaleDateString() : 'Never'}
            </p>
          </div>
        </div>
      </div>

      {/* Leaderboard */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Leaderboard</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 pr-4 font-medium text-gray-600">Rank</th>
                <th className="text-left py-2 pr-4 font-medium text-gray-600">Agent</th>
                <th className="text-right py-2 pr-4 font-medium text-gray-600">Portfolio Value</th>
                <th className="text-left py-2 font-medium text-gray-600">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {report.leaderboard.map((entry) => (
                <tr key={entry.agent_id} className="hover:bg-gray-50 transition-colors">
                  <td className="py-3 pr-4 text-gray-500 font-mono">#{entry.rank}</td>
                  <td className="py-3 pr-4 font-medium text-gray-900">{entry.name}</td>
                  <td className="py-3 pr-4 text-right font-medium text-gray-900 tabular-nums">
                    {formatCurrency(entry.portfolio_value)}
                  </td>
                  <td className="py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        entry.status === 'active'
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {entry.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Tax metrics summary (if present) */}
      {report.tax_metrics && Object.keys(report.tax_metrics).length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Tax Efficiency Summary</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 pr-4 font-medium text-gray-600">Agent</th>
                  <th className="text-right py-2 pr-4 font-medium text-gray-600">Total Tax</th>
                  <th className="text-right py-2 pr-4 font-medium text-gray-600">Short-term</th>
                  <th className="text-right py-2 pr-4 font-medium text-gray-600">Long-term</th>
                  <th className="text-right py-2 pr-4 font-medium text-gray-600">Tax Drag</th>
                  <th className="text-right py-2 font-medium text-gray-600">Avg Hold</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {Object.entries(report.tax_metrics).map(([agentId, metrics]) => {
                  const leaderboardEntry = report.leaderboard.find((e) => e.agent_id === agentId);
                  const agentName = leaderboardEntry?.name ?? agentId;
                  return (
                    <tr key={agentId} className="hover:bg-gray-50 transition-colors">
                      <td className="py-3 pr-4 font-medium text-gray-900">{agentName}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-gray-900">
                        {formatCurrency(metrics.total_tax)}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-amber-600">
                        {formatCurrency(metrics.short_term_tax)}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-emerald-600">
                        {formatCurrency(metrics.long_term_tax)}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-gray-700">
                        {formatPct(metrics.tax_drag_pct)}
                      </td>
                      <td className="py-3 text-right tabular-nums text-gray-700">
                        {metrics.avg_holding_period_days.toFixed(1)}d
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
