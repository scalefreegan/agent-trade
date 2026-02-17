import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import type { Portfolio } from '../../api/types';

interface PositionAllocationChartProps {
  portfolio: Portfolio;
}

export function PositionAllocationChart({ portfolio }: PositionAllocationChartProps) {
  const BRAND_COLORS = [
    '#007F5F', // brand-900
    '#2B9348', // brand-800
    '#55A630', // brand-700
    '#80B918', // brand-600
    '#AACC00', // brand-500
    '#BFD200', // brand-400
  ];
  const CASH_COLOR = '#6B7280';

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Prepare chart data
  const chartData = [];
  let totalValue = portfolio.cash;

  // Add stock positions
  Object.values(portfolio.positions).forEach((position) => {
    const value = position.current_value || 0;
    totalValue += value;
    chartData.push({
      symbol: position.symbol,
      value: value,
      isCash: false,
    });
  });

  // Add cash
  chartData.push({
    symbol: 'CASH',
    value: portfolio.cash,
    isCash: true,
  });

  // Sort by value descending
  chartData.sort((a, b) => b.value - a.value);

  // Assign colors
  const dataWithColors = chartData.map((item, idx) => ({
    ...item,
    color: item.isCash ? CASH_COLOR : BRAND_COLORS[idx % BRAND_COLORS.length],
    percentage: totalValue > 0 ? (item.value / totalValue) * 100 : 0,
  }));

  return (
    <div className="position-allocation-chart">
      <style>{`
        .position-allocation-chart {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
          --text-primary: #111827;
          --text-secondary: #6B7280;
          --text-tertiary: #9CA3AF;
          --border: #E5E7EB;
        }

        .chart-container {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 2rem;
          align-items: center;
        }

        @media (max-width: 768px) {
          .chart-container {
            grid-template-columns: 1fr;
            gap: 1.5rem;
          }
        }

        /* Chart Area */
        .chart-wrapper {
          position: relative;
          height: 280px;
        }

        .chart-center-label {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          text-align: center;
          pointer-events: none;
        }

        .chart-center-title {
          font-size: 0.625rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--text-tertiary);
          margin-bottom: 0.375rem;
        }

        .chart-center-value {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text-primary);
          letter-spacing: -0.02em;
        }

        /* Legend */
        .legend-container {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .legend-header {
          font-size: 0.6875rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--text-tertiary);
          padding-bottom: 0.75rem;
          border-bottom: 1px solid var(--border);
          margin-bottom: 0.25rem;
        }

        .legend-item {
          display: grid;
          grid-template-columns: 20px 1fr auto auto;
          align-items: center;
          gap: 0.75rem;
          padding: 0.625rem 0.75rem;
          border-radius: 0.375rem;
          transition: all 0.15s ease;
          cursor: default;
        }

        .legend-item:hover {
          background: #F9FAFB;
        }

        .legend-color {
          width: 20px;
          height: 20px;
          border-radius: 0.25rem;
          position: relative;
          overflow: hidden;
        }

        .legend-color::after {
          content: '';
          position: absolute;
          inset: 0;
          border: 1px solid rgba(0, 0, 0, 0.08);
          border-radius: 0.25rem;
        }

        .legend-symbol {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.8125rem;
          font-weight: 700;
          color: var(--text-primary);
          letter-spacing: -0.01em;
        }

        .legend-symbol.cash {
          font-weight: 600;
          color: var(--text-secondary);
        }

        .legend-percentage {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.8125rem;
          font-weight: 600;
          color: var(--text-secondary);
          text-align: right;
          min-width: 48px;
        }

        .legend-value {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.8125rem;
          color: var(--text-primary);
          text-align: right;
          min-width: 80px;
          font-weight: 500;
        }

        /* Empty State */
        .empty-state {
          height: 280px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          color: var(--text-tertiary);
          grid-column: 1 / -1;
        }

        .empty-state-icon {
          width: 48px;
          height: 48px;
          margin-bottom: 1rem;
          opacity: 0.3;
        }

        .empty-state-text {
          font-size: 0.875rem;
          font-weight: 500;
        }
      `}</style>

      <div className="chart-container">
        {totalValue === 0 ? (
          <div className="empty-state">
            <svg className="empty-state-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <div className="empty-state-text">No allocation data</div>
          </div>
        ) : (
          <>
            {/* Chart */}
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={dataWithColors}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    animationBegin={0}
                    animationDuration={800}
                    animationEasing="ease-out"
                  >
                    {dataWithColors.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.color}
                        stroke="white"
                        strokeWidth={2}
                      />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>

              <div className="chart-center-label">
                <div className="chart-center-title">Total Value</div>
                <div className="chart-center-value">{formatCurrency(totalValue)}</div>
              </div>
            </div>

            {/* Legend */}
            <div className="legend-container">
              <div className="legend-header">Allocation</div>
              {dataWithColors.map((item, idx) => (
                <div key={idx} className="legend-item">
                  <div
                    className="legend-color"
                    style={{ backgroundColor: item.color }}
                  />
                  <div className={`legend-symbol ${item.isCash ? 'cash' : ''}`}>
                    {item.symbol}
                  </div>
                  <div className="legend-percentage">
                    {item.percentage.toFixed(1)}%
                  </div>
                  <div className="legend-value">
                    {formatCurrency(item.value)}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
