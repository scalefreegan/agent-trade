import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { PerformanceDataPoint } from '../../api/types';

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
    const gainPct = ((gain / startingCapital) * 100);

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
  const currentValue = currentData?.value || startingCapital;
  const currentGain = currentData?.gain || 0;
  const currentGainPct = currentData?.gainPct || 0;

  return (
    <div className="agent-performance-chart">
      <style>{`
        .agent-performance-chart {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        }

        .performance-stats {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .stat-card {
          background: white;
          border: 1px solid #E5E7EB;
          border-radius: 0.5rem;
          padding: 1.25rem;
        }

        .stat-label {
          font-size: 0.6875rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: #9CA3AF;
          margin-bottom: 0.5rem;
        }

        .stat-value {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 1.5rem;
          font-weight: 700;
          color: #111827;
          line-height: 1.2;
        }

        .stat-value.gain {
          color: #2B9348;
        }

        .stat-value.loss {
          color: #DC2626;
        }

        .stat-secondary {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.875rem;
          color: #6B7280;
          margin-top: 0.25rem;
        }

        .chart-container {
          background: white;
          border: 1px solid #E5E7EB;
          border-radius: 0.5rem;
          padding: 1.5rem;
        }

        .chart-title {
          font-size: 0.875rem;
          font-weight: 600;
          color: #374151;
          margin-bottom: 1rem;
        }

        .empty-state {
          text-align: center;
          padding: 4rem 1rem;
          color: #9CA3AF;
        }
      `}</style>

      {/* Stats Summary */}
      <div className="performance-stats">
        <div className="stat-card">
          <div className="stat-label">Current Value</div>
          <div className="stat-value">{formatCurrency(currentValue)}</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Total Gain/Loss</div>
          <div className={`stat-value ${currentGain >= 0 ? 'gain' : 'loss'}`}>
            {currentGain >= 0 ? '+' : ''}{formatCurrency(currentGain)}
          </div>
          <div className="stat-secondary">
            {currentGainPct >= 0 ? '+' : ''}{currentGainPct.toFixed(2)}%
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Starting Capital</div>
          <div className="stat-value">{formatCurrency(startingCapital)}</div>
        </div>
      </div>

      {/* Line Chart */}
      {chartData.length === 0 ? (
        <div className="empty-state">No performance data available</div>
      ) : (
        <div className="chart-container">
          <div className="chart-title">Portfolio Value Over Time</div>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis
                dataKey="trading_day"
                stroke="#6B7280"
                style={{ fontSize: '0.75rem' }}
                label={{ value: 'Trading Day', position: 'insideBottom', offset: -5, style: { fontSize: '0.75rem', fill: '#6B7280' } }}
              />
              <YAxis
                stroke="#6B7280"
                style={{ fontSize: '0.75rem' }}
                tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
                label={{ value: 'Portfolio Value', angle: -90, position: 'insideLeft', style: { fontSize: '0.75rem', fill: '#6B7280' } }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #E5E7EB',
                  borderRadius: '0.375rem',
                  padding: '0.75rem',
                }}
                labelStyle={{ fontWeight: 600, marginBottom: '0.5rem', color: '#111827' }}
                formatter={(value: number, name: string) => {
                  if (name === 'value') {
                    return [formatCurrency(value), 'Portfolio Value'];
                  }
                  if (name === 'gain') {
                    return [formatCurrency(value), 'Gain/Loss'];
                  }
                  return [value, name];
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
        </div>
      )}
    </div>
  );
}
