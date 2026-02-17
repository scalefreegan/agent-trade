import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import type { Portfolio } from '../../api/types';
import { Card } from '../ui/Card';

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

  if (totalValue === 0) {
    return (
      <Card>
        <div className="flex flex-col items-center justify-center h-[280px] text-muted-foreground">
          <svg className="w-12 h-12 mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <div className="text-sm font-medium">No allocation data</div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        {/* Chart */}
        <div className="relative h-[280px]">
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
                    stroke="var(--card)"
                    strokeWidth={2}
                  />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          {/* Center label */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center pointer-events-none">
            <div className="text-[0.625rem] font-semibold tracking-widest uppercase text-muted-foreground mb-1">Total Value</div>
            <div className="font-mono text-2xl font-bold text-foreground tracking-tight">{formatCurrency(totalValue)}</div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-col gap-2">
          <div className="text-xs font-semibold tracking-widest uppercase text-muted-foreground pb-3 border-b border-border mb-1">
            Allocation
          </div>
          {dataWithColors.map((item, idx) => (
            <div key={idx} className="grid items-center gap-3 px-3 py-2.5 rounded-md hover:bg-muted transition-colors" style={{ gridTemplateColumns: '20px 1fr auto auto' }}>
              <div
                className="w-5 h-5 rounded relative overflow-hidden after:absolute after:inset-0 after:border after:border-black/[0.08] after:rounded"
                style={{ backgroundColor: item.color }}
              />
              <div className={`font-mono text-[0.8125rem] font-bold tracking-tight ${item.isCash ? 'text-muted-foreground font-semibold' : 'text-foreground'}`}>
                {item.symbol}
              </div>
              <div className="font-mono text-[0.8125rem] font-semibold text-muted-foreground text-right min-w-[48px]">
                {item.percentage.toFixed(1)}%
              </div>
              <div className="font-mono text-[0.8125rem] text-foreground text-right min-w-[80px] font-medium">
                {formatCurrency(item.value)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
