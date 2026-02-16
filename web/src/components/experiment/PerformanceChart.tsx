import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  TooltipProps,
} from 'recharts';
import type { PerformanceDataPoint } from '../../api/types';
import { getChartColor } from '../../lib/colors';

interface PerformanceChartProps {
  dataPoints: PerformanceDataPoint[];
  agentRankings: Record<string, number>; // agent_id -> rank
  startingCapital?: number;
}

export function PerformanceChart({
  dataPoints,
  agentRankings,
  startingCapital = 100000,
}: PerformanceChartProps) {
  if (dataPoints.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <div className="text-center">
          <p className="text-gray-500 font-medium">No performance data yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Chart will appear after the first trading day
          </p>
        </div>
      </div>
    );
  }

  // Transform data: calculate net gains and structure for Recharts
  const chartData = dataPoints.map((point) => {
    const dataPoint: Record<string, number | string> = {
      day: point.trading_day,
      date: point.date,
    };

    // Calculate net gain for each agent
    Object.entries(point.values).forEach(([agentId, value]) => {
      dataPoint[agentId] = value - startingCapital;
    });

    return dataPoint;
  });

  // Get all unique agent IDs and sort by ranking
  const agentIds = Object.keys(agentRankings).sort(
    (a, b) => agentRankings[a] - agentRankings[b]
  );

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: TooltipProps<number, string>) => {
    if (!active || !payload || payload.length === 0) return null;

    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-4 backdrop-blur-sm bg-white/95">
        <p className="text-sm font-semibold text-gray-900 mb-2 border-b border-gray-100 pb-2">
          Day {label}
        </p>
        <div className="space-y-1.5">
          {payload
            .sort((a, b) => (b.value as number) - (a.value as number))
            .map((entry) => (
              <div key={entry.dataKey} className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className="text-xs text-gray-600 truncate max-w-[120px]">
                    {entry.name}
                  </span>
                </div>
                <span
                  className={`text-xs font-bold font-mono tabular-nums ${
                    (entry.value as number) >= 0 ? 'text-emerald-600' : 'text-red-600'
                  }`}
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
    <div className="w-full bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Performance Over Time</h3>
        <p className="text-sm text-gray-500 mt-1">
          Net gain relative to ${startingCapital.toLocaleString()} starting capital
        </p>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="day"
            label={{ value: 'Trading Day', position: 'insideBottom', offset: -5 }}
            tick={{ fill: '#6b7280', fontSize: 12 }}
            stroke="#d1d5db"
          />
          <YAxis
            label={{
              value: 'Net Gain ($)',
              angle: -90,
              position: 'insideLeft',
              style: { textAnchor: 'middle' },
            }}
            tick={{ fill: '#6b7280', fontSize: 12 }}
            stroke="#d1d5db"
            tickFormatter={(value) =>
              `${value >= 0 ? '+' : ''}${(value / 1000).toFixed(0)}k`
            }
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
            formatter={(value) => (
              <span className="text-sm text-gray-700">{value}</span>
            )}
          />

          {/* Reference line at zero */}
          <Line
            type="monotone"
            dataKey={() => 0}
            stroke="#9ca3af"
            strokeWidth={1}
            strokeDasharray="5 5"
            dot={false}
            legendType="none"
          />

          {/* Agent performance lines */}
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
                activeDot={{
                  r: 5,
                  fill: color,
                  stroke: '#fff',
                  strokeWidth: 2,
                }}
                style={{
                  filter: rank === 1 ? 'drop-shadow(0 0 4px rgba(0, 127, 95, 0.3))' : 'none',
                }}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
