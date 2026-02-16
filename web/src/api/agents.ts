// TanStack Query hooks for agent endpoints
import { useQuery } from '@tanstack/react-query';
import { fetchApi } from './client';
import type {
  AgentDetail,
  AgentStrategy,
  TransactionHistory,
  DecisionLogEntry,
  PortfolioMetrics,
  Portfolio,
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
