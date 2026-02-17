import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { PerformanceDataPoint } from '../../api/types';
import { getChartColor } from '../../lib/colors';
import { Card } from '../ui/Card';
import { useChartTheme } from '../../hooks/useChartTheme';

interface PerformanceChartProps {
  dataPoints: PerformanceDataPoint[];
  agentRankings: Record<string, number>;
  startingCapital?: number;
}

export function PerformanceChart({
  dataPoints,
  agentRankings,
  startingCapital = 100000,
}: PerformanceChartProps) {
  const ct = useChartTheme();
  if (dataPoints.length === 0) {
    return (
      <Card>
        <div className="flex items-center justify-center h-80">
          <div className="text-center">
            <p className="text-muted-foreground font-medium">No performance data yet</p>
            <p className="text-sm text-muted-foreground/60 mt-1">
              Chart will appear after the first trading day
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const chartData = dataPoints.map((point) => {
    const dataPoint: Record<string, number | string> = {
      day: point.trading_day,
      date: point.date,
    };
    Object.entries(point.values).forEach(([agentId, value]) => {
      dataPoint[agentId] = value - startingCapital;
    });
    return dataPoint;
  });

  const agentIds = Object.keys(agentRankings).sort(
    (a, b) => agentRankings[a] - agentRankings[b]
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    return (
      <div
        className="rounded-lg shadow-card-hover p-4"
        style={{ backgroundColor: ct.tooltip.bg, border: `1px solid ${ct.tooltip.border}`, color: ct.tooltip.text }}
      >
        <p
          className="text-sm font-semibold mb-2 pb-2 border-b"
          style={{ color: ct.tooltip.text, borderColor: ct.tooltip.border }}
        >
          Day {label}
        </p>
        <div className="space-y-1.5">
          {[...payload]
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            .sort((a: any, b: any) => ((b.value as number) ?? 0) - ((a.value as number) ?? 0))
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            .map((entry: any) => (
              <div key={entry.dataKey} className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
                  <span className="text-xs truncate max-w-[120px]" style={{ color: ct.axis }}>
                    {entry.name}
                  </span>
                </div>
                <span
                  className="text-xs font-bold font-mono tabular-nums"
                  style={{ color: (entry.value as number) >= 0 ? ct.gainColor : ct.lossColor }}
                >
                  {(entry.value as number) >= 0 ? '+' : ''}
                  ${(entry.value as number).toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </span>
              </div>
            ))}
        </div>
      </div>
    );
  };

  return (
    <Card>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-foreground">Performance Over Time</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Net gain relative to ${startingCapital.toLocaleString()} starting capital
        </p>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={ct.grid} />
          <XAxis
            dataKey="day"
            label={{ value: 'Trading Day', position: 'insideBottom', offset: -5, style: { fill: ct.axis } }}
            tick={{ fill: ct.axis, fontSize: 12 }}
            stroke={ct.axisStroke}
          />
          <YAxis
            label={{
              value: 'Net Gain ($)',
              angle: -90,
              position: 'insideLeft',
              style: { textAnchor: 'middle', fill: ct.axis },
            }}
            tick={{ fill: ct.axis, fontSize: 12 }}
            stroke={ct.axisStroke}
            tickFormatter={(value) =>
              `${value >= 0 ? '+' : ''}${(value / 1000).toFixed(0)}k`
            }
          />
          <Tooltip content={CustomTooltip} />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
            formatter={(value) => (
              <span className="text-sm text-muted-foreground">{value}</span>
            )}
          />

          <Line
            type="monotone"
            dataKey={() => 0}
            stroke={ct.grid}
            strokeWidth={1}
            strokeDasharray="5 5"
            dot={false}
            legendType="none"
          />

          {agentIds.map((agentId) => {
            const rank = agentRankings[agentId];
            const color = getChartColor(rank);

            return (
              <Line
                key={agentId}
                type="monotone"
                dataKey={agentId}
                name={agentId}
                stroke={color}
                strokeWidth={rank === 1 ? 3 : 2}
                dot={false}
                activeDot={{ r: 5, fill: color, stroke: ct.tooltip.bg, strokeWidth: 2 }}
                style={{
                  filter: rank === 1 ? 'drop-shadow(0 0 4px rgba(0, 127, 95, 0.3))' : 'none',
                }}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
