import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { BenchmarkSeries, PerformanceDataPoint } from '../../api/types';
import { Card } from '../ui/Card';
import { MetricCard } from '../ui/MetricCard';
import { useChartTheme } from '../../hooks/useChartTheme';
import { formatCurrency } from '../../lib/format';

// Muted colors for benchmark lines (distinct from agent's primary green)
const BENCHMARK_COLORS = ['#6366f1', '#f59e0b', '#ec4899', '#06b6d4', '#8b5cf6', '#f97316'];

interface AgentPerformanceChartProps {
  dataPoints: PerformanceDataPoint[];
  agentId: string;
  agentName: string;
  startingCapital: number;
  benchmarks?: BenchmarkSeries[];
}

export function AgentPerformanceChart({
  dataPoints,
  agentId,
  agentName,
  startingCapital,
  benchmarks = [],
}: AgentPerformanceChartProps) {
  const ct = useChartTheme();

  // Build a lookup: date -> benchmark value per symbol
  const benchmarkByDate: Record<string, Record<string, number>> = {};
  for (const series of benchmarks) {
    for (const pt of series.data) {
      if (!benchmarkByDate[pt.date]) benchmarkByDate[pt.date] = {};
      benchmarkByDate[pt.date][series.symbol] = pt.value;
    }
  }

  // Filter and transform data for this agent
  const chartData = dataPoints.map((point) => {
    // Use nullish coalescing to preserve 0 values (bankrupt agents)
    const value = point.values[agentId] ?? startingCapital;
    const gain = value - startingCapital;
    const gainPct = startingCapital > 0 ? ((gain / startingCapital) * 100) : 0;

    const benchmarkValues: Record<string, number> = {};
    for (const series of benchmarks) {
      const bv = benchmarkByDate[point.date]?.[series.symbol];
      if (bv !== undefined) benchmarkValues[series.symbol] = bv;
    }

    return {
      date: point.date,
      trading_day: point.trading_day,
      value: value,
      gain: gain,
      gainPct: gainPct,
      ...benchmarkValues,
    };
  });

  // Calculate current stats
  const currentData = chartData[chartData.length - 1];
  const currentValue = currentData?.value ?? startingCapital;
  const currentGain = currentData?.gain ?? 0;
  const currentGainPct = currentData?.gainPct ?? 0;

  const gainColor = currentGain >= 0 ? 'text-gain' : 'text-loss';

  return (
    <div>
      {/* Stats Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card>
          <MetricCard
            label="Current Value"
            value={<span className="font-mono text-2xl font-bold">{formatCurrency(currentValue, 0)}</span>}
          />
        </Card>
        <Card>
          <MetricCard
            label="Total Gain/Loss"
            value={
              <span className={`font-mono text-2xl font-bold ${gainColor}`}>
                {currentGain >= 0 ? '+' : ''}{formatCurrency(currentGain, 0)}
              </span>
            }
            secondary={`${currentGainPct >= 0 ? '+' : ''}${currentGainPct.toFixed(2)}%`}
          />
        </Card>
        <Card>
          <MetricCard
            label="Starting Capital"
            value={<span className="font-mono text-2xl font-bold">{formatCurrency(startingCapital, 0)}</span>}
          />
        </Card>
      </div>

      {/* Line Chart */}
      {chartData.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">No performance data available</div>
      ) : (
        <Card>
          <div className="text-sm font-semibold text-foreground mb-4">Portfolio Value Over Time</div>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={ct.grid} />
              <XAxis
                dataKey="trading_day"
                stroke={ct.axisStroke}
                tick={{ fill: ct.axis, fontSize: 12 }}
                label={{ value: 'Trading Day', position: 'insideBottom', offset: -5, style: { fontSize: '0.75rem', fill: ct.axis } }}
              />
              <YAxis
                stroke={ct.axisStroke}
                tick={{ fill: ct.axis, fontSize: 12 }}
                tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
                label={{ value: 'Portfolio Value', angle: -90, position: 'insideLeft', style: { fontSize: '0.75rem', fill: ct.axis } }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: ct.tooltip.bg,
                  border: `1px solid ${ct.tooltip.border}`,
                  borderRadius: '0.375rem',
                  padding: '0.75rem',
                  color: ct.tooltip.text,
                }}
                labelStyle={{ fontWeight: 600, marginBottom: '0.5rem', color: ct.tooltip.text }}
                formatter={(value: number | undefined, name: string | undefined) => {
                  const v = value ?? 0;
                  if (name === 'value') {
                    return [formatCurrency(v, 0), agentName];
                  }
                  if (name === 'gain') {
                    return [formatCurrency(v, 0), 'Gain/Loss'];
                  }
                  // Benchmark — find label by symbol
                  const series = benchmarks.find((b) => b.symbol === name);
                  return [formatCurrency(v, 0), series?.label ?? name ?? ''];
                }}
                labelFormatter={(day) => `Day ${day}`}
              />
              <Legend
                wrapperStyle={{ paddingTop: '1rem' }}
                iconType="line"
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke={ct.primaryColor}
                strokeWidth={2}
                dot={{ fill: ct.primaryColor, r: 3 }}
                activeDot={{ r: 5, fill: ct.primaryColor, stroke: ct.tooltip.bg, strokeWidth: 2 }}
                name={agentName}
              />
              {benchmarks.map((series, i) => (
                <Line
                  key={series.symbol}
                  type="monotone"
                  dataKey={series.symbol}
                  stroke={BENCHMARK_COLORS[i % BENCHMARK_COLORS.length]}
                  strokeWidth={1.5}
                  strokeDasharray="5 3"
                  dot={false}
                  activeDot={{ r: 4, stroke: ct.tooltip.bg, strokeWidth: 2 }}
                  name={series.symbol}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}
