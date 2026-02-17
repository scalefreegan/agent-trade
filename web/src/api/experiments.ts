// TanStack Query hooks for experiments
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { deleteApi, fetchApi, postApi } from './client';
import type { ExperimentDetail, ExperimentListItem, GameState } from './types';

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

export interface CreateExperimentInput {
  name: string;
  num_agents: number;
  starting_capital: number;
}

export function useCreateExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateExperimentInput) =>
      postApi<ExperimentDetail>('/experiments', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
    },
  });
}

export function useDeleteExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (experimentId: string) => deleteApi(`/experiments/${experimentId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
    },
  });
}
