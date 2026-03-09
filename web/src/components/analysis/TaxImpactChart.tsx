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
import { formatCurrency } from '../../lib/format';

interface TaxMetrics {
  total_tax: number;
  short_term_tax: number;
  long_term_tax: number;
  short_term_gains: number;
  long_term_gains: number;
  gross_proceeds: number;
  tax_drag_pct: number;
  avg_holding_period_days: number;
  num_trades: number;
}

interface TaxImpactChartProps {
  taxMetrics: Record<string, TaxMetrics>;
  agentNames: Record<string, string>;
}

interface ChartDataPoint {
  agentId: string;
  agentName: string;
  shortTermTax: number;
  longTermTax: number;
  totalTax: number;
  taxDragPct: number;
}

export function TaxImpactChart({ taxMetrics, agentNames }: TaxImpactChartProps) {
  const ct = useChartTheme();

  const CustomTooltip = ({ active, payload }: TooltipCallbackProps) => {
    if (!active || !payload?.length) return null;
    const data = payload[0]?.payload as ChartDataPoint | undefined;
    if (!data) return null;

    return (
      <div
        className="rounded-lg shadow-card-hover p-4 min-w-[240px]"
        style={{ backgroundColor: ct.tooltip.bg, border: `1px solid ${ct.tooltip.border}`, color: ct.tooltip.text }}
      >
        <div className="font-semibold mb-3 pb-2 border-b" style={{ borderColor: ct.tooltip.border }}>
          {data.agentName}
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: ct.shortTermColor }} />
              <span className="text-muted-foreground">Short-term</span>
            </div>
            <span className="font-medium" style={{ color: ct.tooltip.text }}>{formatCurrency(data.shortTermTax, 0)}</span>
          </div>
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: ct.longTermColor }} />
              <span className="text-muted-foreground">Long-term</span>
            </div>
            <span className="font-medium" style={{ color: ct.tooltip.text }}>{formatCurrency(data.longTermTax, 0)}</span>
          </div>
          <div className="pt-2 mt-2 border-t flex justify-between items-center" style={{ borderColor: ct.tooltip.border }}>
            <span className="font-medium" style={{ color: ct.tooltip.text }}>Total Tax</span>
            <span className="font-semibold" style={{ color: ct.tooltip.text }}>{formatCurrency(data.totalTax, 0)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground text-xs">Tax Drag</span>
            <span className="font-medium" style={{ color: ct.shortTermColor }}>{(data.taxDragPct ?? 0).toFixed(2)}%</span>
          </div>
        </div>
      </div>
    );
  };

  const CustomLegend = () => (
    <div className="flex justify-center gap-6 mt-6 text-sm">
      <div className="flex items-center gap-2">
        <div className="w-4 h-4 rounded" style={{ backgroundColor: ct.shortTermColor }} />
        <span className="text-muted-foreground">Short-term Capital Gains Tax (≤365 days)</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-4 h-4 rounded" style={{ backgroundColor: ct.longTermColor }} />
        <span className="text-muted-foreground">Long-term Capital Gains Tax (&gt;365 days)</span>
      </div>
    </div>
  );

  // Transform data for Recharts
  const chartData: ChartDataPoint[] = Object.entries(taxMetrics).map(([agentId, metrics]) => ({
    agentId,
    agentName: agentNames[agentId] || agentId,
    shortTermTax: metrics.short_term_tax ?? 0,
    longTermTax: metrics.long_term_tax ?? 0,
    totalTax: metrics.total_tax ?? 0,
    taxDragPct: metrics.tax_drag_pct ?? 0,
  }));

  // Sort by total tax descending for better visual hierarchy
  chartData.sort((a, b) => b.totalTax - a.totalTax);

  if (chartData.length === 0) {
    return (
      <Card>
        <div className="text-center py-12">
          <div className="text-muted-foreground text-lg mb-2">No Tax Data Available</div>
          <p className="text-muted-foreground text-sm">Complete some trades to see tax impact analysis</p>
        </div>
      </Card>
    );
  }

  const totalTaxAll = chartData.reduce((sum, d) => sum + d.totalTax, 0);
  const totalShortTermAll = chartData.reduce((sum, d) => sum + d.shortTermTax, 0);
  const totalLongTermAll = chartData.reduce((sum, d) => sum + d.longTermTax, 0);

  return (
    <Card>
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-foreground mb-1">Tax Impact Analysis</h3>
        <p className="text-sm text-muted-foreground">
          Short-term vs. long-term capital gains tax breakdown by agent
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
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
            tick={{ fill: ct.axis, fontSize: 13 }}
            stroke={ct.axisStroke}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(128,128,128,0.08)' }} />
          <Legend content={<CustomLegend />} />

          <Bar
            dataKey="shortTermTax"
            stackId="tax"
            fill={ct.shortTermColor}
            radius={[0, 0, 0, 0]}
            animationDuration={800}
            animationBegin={0}
          />
          <Bar
            dataKey="longTermTax"
            stackId="tax"
            fill={ct.longTermColor}
            radius={[4, 4, 0, 0]}
            animationDuration={800}
            animationBegin={200}
          />
        </BarChart>
      </ResponsiveContainer>

      {/* Summary Stats */}
      <div className="mt-8 pt-6 border-t border-border grid grid-cols-3 gap-4">
        <MetricCard
          label="Total Taxes Paid"
          value={<span className="font-mono text-2xl font-bold text-foreground">{formatCurrency(totalTaxAll, 0)}</span>}
        />
        <MetricCard
          label="Short-term"
          value={<span className="font-mono text-2xl font-bold" style={{ color: ct.shortTermColor }}>{formatCurrency(totalShortTermAll, 0)}</span>}
        />
        <MetricCard
          label="Long-term"
          value={<span className="font-mono text-2xl font-bold" style={{ color: ct.longTermColor }}>{formatCurrency(totalLongTermAll, 0)}</span>}
        />
      </div>
    </Card>
  );
}
