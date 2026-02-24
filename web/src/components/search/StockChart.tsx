import { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { TooltipContentProps } from 'recharts';
import { useStockHistory } from '../../api/search';
import { useChartTheme } from '../../hooks/useChartTheme';
import { Card } from '../ui/Card';

const PERIODS = [
  { value: '1d', label: '1D' },
  { value: '5d', label: '5D' },
  { value: '1mo', label: '1M' },
  { value: '3mo', label: '3M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '5y', label: '5Y' },
] as const;

type ViewMode = 'price' | 'percent';

interface StockChartProps {
  symbol: string;
}

export function StockChart({ symbol }: StockChartProps) {
  const [period, setPeriod] = useState('3mo');
  const [viewMode, setViewMode] = useState<ViewMode>('price');
  const { data, isLoading, error } = useStockHistory(symbol, period);
  const ct = useChartTheme();

  const rawData =
    data?.data.map((p) => ({
      date: p.date,
      close: p.close,
    })) ?? [];

  const basePrice = rawData.length > 0 ? rawData[0].close : 0;

  const chartData =
    viewMode === 'percent' && basePrice !== 0
      ? rawData.map((p) => ({
          date: p.date,
          close: ((p.close - basePrice) / basePrice) * 100,
        }))
      : rawData;

  // Determine if price went up or down over the period
  const isGain =
    chartData.length >= 2
      ? chartData[chartData.length - 1].close >= chartData[0].close
      : true;
  const lineColor = isGain ? ct.gainColor : ct.lossColor;

  const CustomTooltip = ({ active, payload, label }: TooltipContentProps<number, string>) => {
    if (!active || !payload || payload.length === 0) return null;
    const val = payload[0].value as number;
    return (
      <div
        className="rounded-lg px-3 py-2 text-sm shadow-lg"
        style={{
          backgroundColor: ct.tooltip.bg,
          border: `1px solid ${ct.tooltip.border}`,
          color: ct.tooltip.text,
        }}
      >
        <p className="font-medium">{label}</p>
        <p style={{ color: lineColor }}>
          {viewMode === 'percent'
            ? `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`
            : `$${val.toFixed(2)}`}
        </p>
      </div>
    );
  };

  const toggleBtnClass = (active: boolean) =>
    `px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
      active
        ? 'bg-primary text-primary-foreground'
        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
    }`;

  return (
    <Card className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-foreground">Price History</h3>
          <div className="flex gap-0.5 ml-2 bg-muted rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('price')}
              className={toggleBtnClass(viewMode === 'price')}
            >
              $
            </button>
            <button
              onClick={() => setViewMode('percent')}
              className={toggleBtnClass(viewMode === 'percent')}
            >
              %
            </button>
          </div>
        </div>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={toggleBtnClass(period === p.value)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0">
        {isLoading ? (
          <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
            Loading chart...
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center text-loss text-sm">
            Failed to load chart data
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
            No data available for this period
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <defs>
                <linearGradient id={`gradient-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={lineColor} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={ct.grid} vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fill: ct.axis, fontSize: 11 }}
                stroke={ct.axisStroke}
                tickLine={false}
                axisLine={false}
                minTickGap={40}
              />
              <YAxis
                tick={{ fill: ct.axis, fontSize: 11 }}
                stroke={ct.axisStroke}
                tickLine={false}
                axisLine={false}
                domain={['auto', 'auto']}
                tickFormatter={
                  viewMode === 'percent'
                    ? (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`
                    : (v: number) => `$${v.toFixed(0)}`
                }
                width={55}
              />
              <Tooltip content={CustomTooltip} />
              <Area
                type="monotone"
                dataKey="close"
                stroke={lineColor}
                strokeWidth={2}
                fill={`url(#gradient-${symbol})`}
                dot={false}
                activeDot={{ r: 4, fill: lineColor }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}
