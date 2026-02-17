import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface TooltipCallbackProps {
  active?: boolean;
  payload?: Array<{ payload?: unknown }>;
}
import { useChartTheme } from '../../hooks/useChartTheme';
import { Card } from '../ui/Card';
import { MetricCard } from '../ui/MetricCard';

interface HoldingPeriodDistribution {
  '0-30': number;
  '31-90': number;
  '91-180': number;
  '181-365': number;
  '365+': number;
}

interface HoldingPeriodChartProps {
  holdingPeriods: Record<string, HoldingPeriodDistribution>;
  agentNames: Record<string, string>;
}

interface ChartDataPoint {
  agentName: string;
  '0-30': number;
  '31-90': number;
  '91-180': number;
  '181-365': number;
  '365+': number;
  total: number;
}

const bucketLabels: Record<keyof HoldingPeriodDistribution, string> = {
  '0-30': '0-30 days',
  '31-90': '31-90 days',
  '91-180': '91-180 days',
  '181-365': '181-365 days',
  '365+': '365+ days',
};

export function HoldingPeriodChart({ holdingPeriods, agentNames }: HoldingPeriodChartProps) {
  const ct = useChartTheme();
  const bucketColors = ct.holdingBucketColors;

  const CustomTooltip = ({ active, payload }: TooltipCallbackProps) => {
    if (!active || !payload?.length) return null;
    const data = payload[0]?.payload as ChartDataPoint | undefined;
    if (!data) return null;

    return (
      <div
        className="rounded-lg shadow-card-hover p-4 min-w-[220px]"
        style={{ backgroundColor: ct.tooltip.bg, border: `1px solid ${ct.tooltip.border}`, color: ct.tooltip.text }}
      >
        <div className="font-semibold mb-3 pb-2 border-b" style={{ borderColor: ct.tooltip.border }}>
          {data.agentName}
        </div>
        <div className="space-y-2 text-sm">
          {Object.entries(bucketLabels).map(([key, label]) => {
            const value = data[key as keyof HoldingPeriodDistribution];
            const percentage = data.total > 0 ? ((value / data.total) * 100).toFixed(1) : '0.0';
            return (
              <div key={key} className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: bucketColors[key] }} />
                  <span className="text-muted-foreground">{label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium" style={{ color: ct.tooltip.text }}>{value}</span>
                  <span className="text-muted-foreground text-xs">({percentage}%)</span>
                </div>
              </div>
            );
          })}
          <div className="pt-2 mt-2 border-t flex justify-between items-center" style={{ borderColor: ct.tooltip.border }}>
            <span className="font-medium" style={{ color: ct.tooltip.text }}>Total Trades</span>
            <span className="font-semibold" style={{ color: ct.tooltip.text }}>{data.total}</span>
          </div>
        </div>
      </div>
    );
  };

  const CustomLegend = () => (
    <div className="flex flex-wrap justify-center gap-4 mt-6 text-xs">
      {Object.entries(bucketLabels).map(([key, label]) => (
        <div key={key} className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: bucketColors[key] }} />
          <span className="text-muted-foreground">{label}</span>
        </div>
      ))}
    </div>
  );

  // Transform data for Recharts
  const chartData: ChartDataPoint[] = Object.entries(holdingPeriods).map(([agentId, distribution]) => {
    const total = Object.values(distribution).reduce((sum, val) => sum + val, 0);
    return {
      agentName: agentNames[agentId] || agentId,
      '0-30': distribution['0-30'],
      '31-90': distribution['31-90'],
      '91-180': distribution['91-180'],
      '181-365': distribution['181-365'],
      '365+': distribution['365+'],
      total,
    };
  });

  // Sort by total trades descending
  chartData.sort((a, b) => b.total - a.total);

  if (chartData.length === 0) {
    return (
      <Card>
        <div className="text-center py-12">
          <div className="text-muted-foreground text-lg mb-2">No Holding Period Data</div>
          <p className="text-muted-foreground text-sm">Complete some sell transactions to see holding period analysis</p>
        </div>
      </Card>
    );
  }

  // Calculate aggregate statistics
  const totalLongTerm = chartData.reduce((sum, d) => sum + d['365+'], 0);
  const totalShortTerm = chartData.reduce(
    (sum, d) => sum + d['0-30'] + d['31-90'] + d['91-180'] + d['181-365'],
    0
  );
  const totalTrades = totalLongTerm + totalShortTerm;
  const longTermPct = totalTrades > 0 ? ((totalLongTerm / totalTrades) * 100).toFixed(1) : '0.0';

  return (
    <Card>
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-foreground mb-1">Holding Period Distribution</h3>
        <p className="text-sm text-muted-foreground">
          Trade frequency by holding period bucket (365+ days qualifies for long-term capital gains rates)
        </p>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
          barGap={8}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={ct.grid} vertical={false} />
          <XAxis
            dataKey="agentName"
            angle={-45}
            textAnchor="end"
            height={100}
            tick={{ fill: ct.axis, fontSize: 13 }}
            stroke={ct.axisStroke}
          />
          <YAxis
            label={{ value: 'Number of Trades', angle: -90, position: 'insideLeft', style: { fill: ct.axis } }}
            tick={{ fill: ct.axis, fontSize: 13 }}
            stroke={ct.axisStroke}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(128,128,128,0.08)' }} />
          <Legend content={<CustomLegend />} />

          <Bar dataKey="0-30" stackId="holding" fill={bucketColors['0-30']} animationDuration={800} animationBegin={0} />
          <Bar dataKey="31-90" stackId="holding" fill={bucketColors['31-90']} animationDuration={800} animationBegin={100} />
          <Bar dataKey="91-180" stackId="holding" fill={bucketColors['91-180']} animationDuration={800} animationBegin={200} />
          <Bar dataKey="181-365" stackId="holding" fill={bucketColors['181-365']} animationDuration={800} animationBegin={300} />
          <Bar dataKey="365+" stackId="holding" fill={bucketColors['365+']} radius={[4, 4, 0, 0]} animationDuration={800} animationBegin={400} />
        </BarChart>
      </ResponsiveContainer>

      {/* Summary Stats */}
      <div className="mt-8 pt-6 border-t border-border grid grid-cols-3 gap-4">
        <MetricCard
          label="Total Sell Trades"
          value={<span className="font-mono text-2xl font-bold text-foreground">{totalTrades}</span>}
        />
        <MetricCard
          label="Short-term (<365d)"
          value={<span className="font-mono text-2xl font-bold" style={{ color: bucketColors['0-30'] }}>{totalShortTerm}</span>}
        />
        <MetricCard
          label="Long-term (365+d)"
          value={
            <span className="font-mono text-2xl font-bold" style={{ color: bucketColors['365+'] }}>
              {totalLongTerm}
              <span className="text-sm text-muted-foreground ml-2">({longTermPct}%)</span>
            </span>
          }
        />
      </div>

      {/* Educational note */}
      <div className="mt-6 p-4 rounded-lg border" style={{ backgroundColor: `${bucketColors['365+']}15`, borderColor: `${bucketColors['365+']}40` }}>
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center mt-0.5" style={{ backgroundColor: bucketColors['365+'] }}>
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="text-sm" style={{ color: ct.tooltip.text }}>
            <span className="font-medium">Tax Efficiency Tip:</span> Positions held for 365+ days qualify for
            long-term capital gains treatment (15% rate vs. 35% short-term rate in this simulation).
          </div>
        </div>
      </div>
    </Card>
  );
}
