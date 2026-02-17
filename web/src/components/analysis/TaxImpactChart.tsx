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

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload as ChartDataPoint;

  return (
    <div className="bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg shadow-lg p-4 min-w-[240px]">
      <div className="font-semibold text-gray-900 mb-3 pb-2 border-b border-gray-100">
        {data.agentName}
      </div>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm bg-amber-500"></div>
            <span className="text-gray-600">Short-term</span>
          </div>
          <span className="font-medium text-gray-900">{formatCurrency(data.shortTermTax)}</span>
        </div>
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm bg-emerald-600"></div>
            <span className="text-gray-600">Long-term</span>
          </div>
          <span className="font-medium text-gray-900">{formatCurrency(data.longTermTax)}</span>
        </div>
        <div className="pt-2 mt-2 border-t border-gray-100 flex justify-between items-center">
          <span className="text-gray-700 font-medium">Total Tax</span>
          <span className="font-semibold text-gray-900">{formatCurrency(data.totalTax)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-gray-600 text-xs">Tax Drag</span>
          <span className="font-medium text-amber-600">{data.taxDragPct.toFixed(2)}%</span>
        </div>
      </div>
    </div>
  );
};

const CustomLegend = () => {
  return (
    <div className="flex justify-center gap-6 mt-6 text-sm">
      <div className="flex items-center gap-2">
        <div className="w-4 h-4 rounded bg-amber-500"></div>
        <span className="text-gray-700">Short-term Capital Gains Tax (≤365 days)</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-4 h-4 rounded bg-emerald-600"></div>
        <span className="text-gray-700">Long-term Capital Gains Tax ({'>'}365 days)</span>
      </div>
    </div>
  );
};

export function TaxImpactChart({ taxMetrics, agentNames }: TaxImpactChartProps) {
  // Transform data for Recharts
  const chartData: ChartDataPoint[] = Object.entries(taxMetrics).map(([agentId, metrics]) => ({
    agentId,
    agentName: agentNames[agentId] || agentId,
    shortTermTax: metrics.short_term_tax,
    longTermTax: metrics.long_term_tax,
    totalTax: metrics.total_tax,
    taxDragPct: metrics.tax_drag_pct,
  }));

  // Sort by total tax descending for better visual hierarchy
  chartData.sort((a, b) => b.totalTax - a.totalTax);

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12">
        <div className="text-center">
          <div className="text-gray-400 text-lg mb-2">No Tax Data Available</div>
          <p className="text-gray-500 text-sm">Complete some trades to see tax impact analysis</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-1">Tax Impact Analysis</h3>
        <p className="text-sm text-gray-600">
          Short-term vs. long-term capital gains tax breakdown by agent
        </p>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
          barGap={8}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
          <XAxis
            dataKey="agentName"
            angle={-45}
            textAnchor="end"
            height={100}
            tick={{ fill: '#6b7280', fontSize: 13 }}
            stroke="#9ca3af"
          />
          <YAxis
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
            tick={{ fill: '#6b7280', fontSize: 13 }}
            stroke="#9ca3af"
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }} />
          <Legend content={<CustomLegend />} />

          {/* Short-term tax - amber/orange tones */}
          <Bar
            dataKey="shortTermTax"
            stackId="tax"
            fill="#f59e0b"
            radius={[0, 0, 0, 0]}
            animationDuration={800}
            animationBegin={0}
          />

          {/* Long-term tax - emerald green tones */}
          <Bar
            dataKey="longTermTax"
            stackId="tax"
            fill="#059669"
            radius={[4, 4, 0, 0]}
            animationDuration={800}
            animationBegin={200}
          />
        </BarChart>
      </ResponsiveContainer>

      {/* Summary Stats */}
      <div className="mt-8 pt-6 border-t border-gray-100 grid grid-cols-3 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">
            {formatCurrency(chartData.reduce((sum, d) => sum + d.totalTax, 0))}
          </div>
          <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">Total Taxes Paid</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-amber-600">
            {formatCurrency(chartData.reduce((sum, d) => sum + d.shortTermTax, 0))}
          </div>
          <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">Short-term</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-emerald-600">
            {formatCurrency(chartData.reduce((sum, d) => sum + d.longTermTax, 0))}
          </div>
          <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">Long-term</div>
        </div>
      </div>
    </div>
  );
}
