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

interface HoldingPeriodDistribution {
  '0-30': number;
  '31-90': number;
  '91-180': number;
  '181-365': number;
  '365+': number;
}

interface HoldingPeriodChartProps {
  holdingPeriods: Record<string, HoldingPeriodDistribution>;
  agentNames: Record<string, string>;
}

interface ChartDataPoint {
  agentName: string;
  '0-30': number;
  '31-90': number;
  '91-180': number;
  '181-365': number;
  '365+': number;
  total: number;
}

const bucketLabels: Record<keyof HoldingPeriodDistribution, string> = {
  '0-30': '0-30 days',
  '31-90': '31-90 days',
  '91-180': '91-180 days',
  '181-365': '181-365 days',
  '365+': '365+ days',
};

// Color scale from warm (short) to cool (long)
const bucketColors: Record<keyof HoldingPeriodDistribution, string> = {
  '0-30': '#dc2626',      // red-600 - very short term
  '31-90': '#f59e0b',     // amber-500 - short term
  '91-180': '#eab308',    // yellow-500 - medium term
  '181-365': '#84cc16',   // lime-500 - approaching long term
  '365+': '#059669',      // emerald-600 - long term (tax advantaged)
};

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload as ChartDataPoint;

  return (
    <div className="bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg shadow-lg p-4 min-w-[220px]">
      <div className="font-semibold text-gray-900 mb-3 pb-2 border-b border-gray-100">
        {data.agentName}
      </div>
      <div className="space-y-2 text-sm">
        {Object.entries(bucketLabels).map(([key, label]) => {
          const value = data[key as keyof HoldingPeriodDistribution];
          const percentage = data.total > 0 ? ((value / data.total) * 100).toFixed(1) : '0.0';
          return (
            <div key={key} className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-sm"
                  style={{ backgroundColor: bucketColors[key as keyof HoldingPeriodDistribution] }}
                ></div>
                <span className="text-gray-600">{label}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900">{value}</span>
                <span className="text-gray-500 text-xs">({percentage}%)</span>
              </div>
            </div>
          );
        })}
        <div className="pt-2 mt-2 border-t border-gray-100 flex justify-between items-center">
          <span className="text-gray-700 font-medium">Total Trades</span>
          <span className="font-semibold text-gray-900">{data.total}</span>
        </div>
      </div>
    </div>
  );
};

const CustomLegend = () => {
  return (
    <div className="flex flex-wrap justify-center gap-4 mt-6 text-xs">
      {Object.entries(bucketLabels).map(([key, label]) => (
        <div key={key} className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded"
            style={{ backgroundColor: bucketColors[key as keyof HoldingPeriodDistribution] }}
          ></div>
          <span className="text-gray-700">{label}</span>
        </div>
      ))}
    </div>
  );
};

export function HoldingPeriodChart({ holdingPeriods, agentNames }: HoldingPeriodChartProps) {
  // Transform data for Recharts
  const chartData: ChartDataPoint[] = Object.entries(holdingPeriods).map(([agentId, distribution]) => {
    const total = Object.values(distribution).reduce((sum, val) => sum + val, 0);
    return {
      agentName: agentNames[agentId] || agentId,
      '0-30': distribution['0-30'],
      '31-90': distribution['31-90'],
      '91-180': distribution['91-180'],
      '181-365': distribution['181-365'],
      '365+': distribution['365+'],
      total,
    };
  });

  // Sort by total trades descending
  chartData.sort((a, b) => b.total - a.total);

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12">
        <div className="text-center">
          <div className="text-gray-400 text-lg mb-2">No Holding Period Data</div>
          <p className="text-gray-500 text-sm">Complete some sell transactions to see holding period analysis</p>
        </div>
      </div>
    );
  }

  // Calculate aggregate statistics
  const totalLongTerm = chartData.reduce((sum, d) => sum + d['365+'], 0);
  const totalShortTerm = chartData.reduce(
    (sum, d) => sum + d['0-30'] + d['31-90'] + d['91-180'] + d['181-365'],
    0
  );
  const totalTrades = totalLongTerm + totalShortTerm;
  const longTermPct = totalTrades > 0 ? ((totalLongTerm / totalTrades) * 100).toFixed(1) : '0.0';

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-1">Holding Period Distribution</h3>
        <p className="text-sm text-gray-600">
          Trade frequency by holding period bucket (365+ days qualifies for long-term capital gains rates)
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
            label={{ value: 'Number of Trades', angle: -90, position: 'insideLeft', style: { fill: '#6b7280' } }}
            tick={{ fill: '#6b7280', fontSize: 13 }}
            stroke="#9ca3af"
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }} />
          <Legend content={<CustomLegend />} />

          {/* Bars ordered from shortest to longest holding period */}
          <Bar
            dataKey="0-30"
            stackId="holding"
            fill={bucketColors['0-30']}
            animationDuration={800}
            animationBegin={0}
          />
          <Bar
            dataKey="31-90"
            stackId="holding"
            fill={bucketColors['31-90']}
            animationDuration={800}
            animationBegin={100}
          />
          <Bar
            dataKey="91-180"
            stackId="holding"
            fill={bucketColors['91-180']}
            animationDuration={800}
            animationBegin={200}
          />
          <Bar
            dataKey="181-365"
            stackId="holding"
            fill={bucketColors['181-365']}
            animationDuration={800}
            animationBegin={300}
          />
          <Bar
            dataKey="365+"
            stackId="holding"
            fill={bucketColors['365+']}
            radius={[4, 4, 0, 0]}
            animationDuration={800}
            animationBegin={400}
          />
        </BarChart>
      </ResponsiveContainer>

      {/* Summary Stats */}
      <div className="mt-8 pt-6 border-t border-gray-100 grid grid-cols-3 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">{totalTrades}</div>
          <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">Total Sell Trades</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-red-600">{totalShortTerm}</div>
          <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">Short-term (&lt;365d)</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-emerald-600">
            {totalLongTerm}
            <span className="text-sm text-gray-500 ml-2">({longTermPct}%)</span>
          </div>
          <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">Long-term (365+d)</div>
        </div>
      </div>

      {/* Educational note */}
      <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-600 flex items-center justify-center mt-0.5">
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="text-sm text-emerald-900">
            <span className="font-medium">Tax Efficiency Tip:</span> Positions held for 365+ days qualify for
            long-term capital gains treatment (15% rate vs. 35% short-term rate in this simulation).
          </div>
        </div>
      </div>
    </div>
  );
}
