import { useQuery } from '@tanstack/react-query';
import { fetchApi } from './client';

// Tax metrics per agent
export interface TaxMetrics {
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

export interface TaxMetricsResponse {
  [agentId: string]: TaxMetrics;
}

// Holding period distribution per agent
export interface HoldingPeriodDistribution {
  '0-30': number;
  '31-90': number;
  '91-180': number;
  '181-365': number;
  '365+': number;
}

export interface HoldingPeriodResponse {
  [agentId: string]: HoldingPeriodDistribution;
}

// Full experiment report
export interface LeaderboardEntry {
  rank: number;
  agent_id: string;
  name: string;
  portfolio_value: number;
  status: string;
}

export interface ExperimentReport {
  experiment_id: string;
  name: string;
  status: string;
  trading_day: number;
  last_run: string | null;
  num_agents_total: number;
  num_agents_active: number;
  leaderboard: LeaderboardEntry[];
  tax_metrics?: TaxMetricsResponse;
  holding_period_distribution?: HoldingPeriodResponse;
}

export function useTaxMetrics(experimentId: string) {
  return useQuery({
    queryKey: ['tax-metrics', experimentId],
    queryFn: () => fetchApi<TaxMetricsResponse>(`/experiments/${experimentId}/tax-metrics`),
    enabled: !!experimentId,
  });
}

export function useHoldingPeriods(experimentId: string) {
  return useQuery({
    queryKey: ['holding-periods', experimentId],
    queryFn: () => fetchApi<HoldingPeriodResponse>(`/experiments/${experimentId}/holding-periods`),
    enabled: !!experimentId,
  });
}

export function useExperimentReport(experimentId: string, includeTaxMetrics = true) {
  return useQuery({
    queryKey: ['experiment-report', experimentId, includeTaxMetrics],
    queryFn: () =>
      fetchApi<ExperimentReport>(
        `/experiments/${experimentId}/report?include_tax_metrics=${includeTaxMetrics}`
      ),
    enabled: !!experimentId,
  });
}
