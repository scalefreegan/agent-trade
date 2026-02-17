import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { PerformanceDataPoint } from '../../api/types';
import { Card } from '../ui/Card';
import { MetricCard } from '../ui/MetricCard';

interface AgentPerformanceChartProps {
  dataPoints: PerformanceDataPoint[];
  agentId: string;
  agentName: string;
  startingCapital: number;
}

export function AgentPerformanceChart({
  dataPoints,
  agentId,
  agentName,
  startingCapital,
}: AgentPerformanceChartProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Filter and transform data for this agent
  const chartData = dataPoints.map((point) => {
    // Use nullish coalescing to preserve 0 values (bankrupt agents)
    const value = point.values[agentId] ?? startingCapital;
    const gain = value - startingCapital;
    const gainPct = startingCapital > 0 ? ((gain / startingCapital) * 100) : 0;

    return {
      date: point.date,
      trading_day: point.trading_day,
      value: value,
      gain: gain,
      gainPct: gainPct,
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
            value={<span className="font-mono text-2xl font-bold">{formatCurrency(currentValue)}</span>}
          />
        </Card>
        <Card>
          <MetricCard
            label="Total Gain/Loss"
            value={
              <span className={`font-mono text-2xl font-bold ${gainColor}`}>
                {currentGain >= 0 ? '+' : ''}{formatCurrency(currentGain)}
              </span>
            }
            secondary={`${currentGainPct >= 0 ? '+' : ''}${currentGainPct.toFixed(2)}%`}
          />
        </Card>
        <Card>
          <MetricCard
            label="Starting Capital"
            value={<span className="font-mono text-2xl font-bold">{formatCurrency(startingCapital)}</span>}
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
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis
                dataKey="trading_day"
                stroke="var(--muted-foreground)"
                style={{ fontSize: '0.75rem' }}
                label={{ value: 'Trading Day', position: 'insideBottom', offset: -5, style: { fontSize: '0.75rem', fill: 'var(--muted-foreground)' } }}
              />
              <YAxis
                stroke="var(--muted-foreground)"
                style={{ fontSize: '0.75rem' }}
                tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
                label={{ value: 'Portfolio Value', angle: -90, position: 'insideLeft', style: { fontSize: '0.75rem', fill: 'var(--muted-foreground)' } }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '0.375rem',
                  padding: '0.75rem',
                  color: 'var(--foreground)',
                }}
                labelStyle={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--foreground)' }}
                formatter={(value: number | undefined, name: string | undefined) => {
                  const v = value ?? 0;
                  if (name === 'value') {
                    return [formatCurrency(v), 'Portfolio Value'];
                  }
                  if (name === 'gain') {
                    return [formatCurrency(v), 'Gain/Loss'];
                  }
                  return [v, name ?? ''];
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
                stroke="#2B9348"
                strokeWidth={2}
                dot={{ fill: '#2B9348', r: 3 }}
                activeDot={{ r: 5 }}
                name={agentName}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}
