// TanStack Query hooks for agent endpoints
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchApi, patchApi } from './client';
import type {
  AgentDetail,
  AgentStrategy,
  AlertsResponse,
  BenchmarkResponse,
  DecisionLogEntry,
  HoldingsInfo,
  Portfolio,
  PortfolioMetrics,
  TransactionHistory,
  UpdateAgentResponse,
} from './types';

export function useAgentDetail(experimentId: string, agentId: string) {
  return useQuery({
    queryKey: ['agent', experimentId, agentId],
    queryFn: () => fetchApi<AgentDetail>(`/experiments/${experimentId}/agents/${agentId}`),
    enabled: !!experimentId && !!agentId,
  });
}

export function useAgentPortfolio(experimentId: string, agentId: string) {
  return useQuery({
    queryKey: ['agentPortfolio', experimentId, agentId],
    queryFn: () => fetchApi<{ portfolio: Portfolio; metrics: PortfolioMetrics }>(
      `/experiments/${experimentId}/agents/${agentId}/portfolio`
    ),
    enabled: !!experimentId && !!agentId,
  });
}

export function useAgentStrategy(experimentId: string, agentId: string) {
  return useQuery({
    queryKey: ['agentStrategy', experimentId, agentId],
    queryFn: () => fetchApi<AgentStrategy>(`/experiments/${experimentId}/agents/${agentId}/strategy`),
    enabled: !!experimentId && !!agentId,
  });
}

export function useAgentTransactions(experimentId: string, agentId: string) {
  return useQuery({
    queryKey: ['agentTransactions', experimentId, agentId],
    queryFn: () => fetchApi<TransactionHistory>(
      `/experiments/${experimentId}/agents/${agentId}/transactions`
    ),
    enabled: !!experimentId && !!agentId,
  });
}

export function useAgentDecisions(experimentId: string, agentId: string) {
  return useQuery({
    queryKey: ['agentDecisions', experimentId, agentId],
    queryFn: () => fetchApi<DecisionLogEntry[]>(
      `/experiments/${experimentId}/agents/${agentId}/decisions`
    ),
    enabled: !!experimentId && !!agentId,
  });
}

export function useAgentDecision(experimentId: string, agentId: string, date: string) {
  return useQuery({
    queryKey: ['agentDecision', experimentId, agentId, date],
    queryFn: () => fetchApi<{ markdown: string }>(
      `/experiments/${experimentId}/agents/${agentId}/decisions/${date}`
    ),
    enabled: !!experimentId && !!agentId && !!date,
  });
}

export function useAgentHoldings(experimentId: string, agentId: string) {
  return useQuery({
    queryKey: ['agentHoldings', experimentId, agentId],
    queryFn: () => fetchApi<HoldingsInfo>(
      `/experiments/${experimentId}/agents/${agentId}/holdings`
    ),
    enabled: !!experimentId && !!agentId,
  });
}

export function useAgentAlerts(experimentId: string, agentId: string) {
  return useQuery({
    queryKey: ['agentAlerts', experimentId, agentId],
    queryFn: () => fetchApi<AlertsResponse>(
      `/experiments/${experimentId}/agents/${agentId}/alerts`
    ),
    enabled: !!experimentId && !!agentId,
  });
}

export function useAgentBenchmarks(experimentId: string, agentId: string) {
  return useQuery({
    queryKey: ['agentBenchmarks', experimentId, agentId],
    queryFn: () => fetchApi<BenchmarkResponse>(
      `/experiments/${experimentId}/agents/${agentId}/benchmarks`
    ),
    enabled: !!experimentId && !!agentId,
    staleTime: 5 * 60 * 1000, // 5 min — ETF data doesn't change often
  });
}

export function useUpdateAgent(experimentId: string, agentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { name?: string; description?: string | null }) =>
      patchApi<UpdateAgentResponse>(
        `/experiments/${experimentId}/agents/${agentId}`,
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent', experimentId, agentId] });
      queryClient.invalidateQueries({ queryKey: ['gameState', experimentId] });
    },
  });
}
