import { useQuery } from '@tanstack/react-query';
import { fetchApi } from './client';
import type { LeaderboardResponse, PerformanceResponse } from './types';

export function useLeaderboard(experimentId: string) {
  return useQuery({
    queryKey: ['leaderboard', experimentId],
    queryFn: () => fetchApi<LeaderboardResponse>(`/experiments/${experimentId}/leaderboard`),
    enabled: !!experimentId,
  });
}

export function usePerformance(experimentId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['performance', experimentId],
    queryFn: () => fetchApi<PerformanceResponse>(`/experiments/${experimentId}/performance`),
    enabled: !!experimentId && (options?.enabled ?? true),
  });
}
