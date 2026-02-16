import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';
import type { LeaderboardResponse, PerformanceResponse } from './types';

export function useLeaderboard(experimentId: string) {
  return useQuery({
    queryKey: ['leaderboard', experimentId],
    queryFn: async () => {
      const response = await apiClient.get<LeaderboardResponse>(
        `/experiments/${experimentId}/leaderboard`
      );
      return response.data;
    },
    enabled: !!experimentId,
  });
}

export function usePerformance(experimentId: string) {
  return useQuery({
    queryKey: ['performance', experimentId],
    queryFn: async () => {
      const response = await apiClient.get<PerformanceResponse>(
        `/experiments/${experimentId}/performance`
      );
      return response.data;
    },
    enabled: !!experimentId,
  });
}
