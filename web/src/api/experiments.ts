// TanStack Query hooks for experiments
import { useQuery } from '@tanstack/react-query';
import { fetchApi } from './client';
import type { ExperimentListItem, ExperimentDetail, GameState } from './types';

export function useExperiments() {
  return useQuery({
    queryKey: ['experiments'],
    queryFn: () => fetchApi<ExperimentListItem[]>('/experiments'),
  });
}

export function useExperiment(experimentId: string) {
  return useQuery({
    queryKey: ['experiment', experimentId],
    queryFn: () => fetchApi<ExperimentDetail>(`/experiments/${experimentId}`),
    enabled: !!experimentId,
  });
}

export function useGameState(experimentId: string) {
  return useQuery({
    queryKey: ['gameState', experimentId],
    queryFn: () => fetchApi<GameState>(`/experiments/${experimentId}/state`),
    enabled: !!experimentId,
  });
}
