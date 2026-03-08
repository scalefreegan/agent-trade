/**
 * API functions for run control.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError, fetchApi, postApi } from './client';
import type { RunStatus } from './types';

// Re-export so existing `import { RunStatus } from './runs'` still works.
export type { RunStatus } from './types';

/**
 * Start a run for an experiment.
 */
export async function startRun(experimentId: string, signal?: AbortSignal): Promise<RunStatus> {
  return postApi<RunStatus>(`/experiments/${experimentId}/run`, undefined, { signal });
}

/**
 * Get run status for an experiment.
 */
export async function getRunStatus(experimentId: string, signal?: AbortSignal): Promise<RunStatus> {
  try {
    return await fetchApi<RunStatus>(`/experiments/${experimentId}/run/status`, { signal });
  } catch (err) {
    // 404 could mean either "no job" or "experiment not found".
    // Verify the experiment exists before returning idle status.
    if (err instanceof ApiError && err.status === 404) {
      // This will throw if the experiment doesn't exist.
      await fetchApi(`/experiments/${experimentId}`, { signal });

      return {
        job_id: '',
        experiment_id: experimentId,
        status: 'idle',
        started_at: '',
      };
    }
    throw err;
  }
}

/**
 * Hook to get run status.
 */
export function useRunStatus(experimentId: string | null) {
  return useQuery({
    queryKey: ['runStatus', experimentId],
    queryFn: ({ signal }) => getRunStatus(experimentId!, signal),
    enabled: !!experimentId,
    refetchInterval: (query) => {
      return query.state.data?.status === 'running' ? 2000 : false;
    },
  });
}

/**
 * Hook to start a run.
 */
export function useStartRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (experimentId: string) => startRun(experimentId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['runStatus', data.experiment_id] });
    },
  });
}

/**
 * Pause an experiment.
 */
export async function pauseExperiment(experimentId: string, signal?: AbortSignal): Promise<{ status: string; new_status: string }> {
  return postApi<{ status: string; new_status: string }>(`/experiments/${experimentId}/pause`, undefined, { signal });
}

/**
 * Resume an experiment.
 */
export async function resumeExperiment(experimentId: string, signal?: AbortSignal): Promise<{ status: string; new_status: string }> {
  return postApi<{ status: string; new_status: string }>(`/experiments/${experimentId}/resume`, undefined, { signal });
}

/**
 * Hook to pause an experiment.
 */
export function usePauseExperiment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (experimentId: string) => pauseExperiment(experimentId),
    onSuccess: (_data, experimentId) => {
      queryClient.invalidateQueries({ queryKey: ['experiment', experimentId] });
      queryClient.invalidateQueries({ queryKey: ['gameState', experimentId] });
    },
  });
}

/**
 * Hook to resume an experiment.
 */
export function useResumeExperiment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (experimentId: string) => resumeExperiment(experimentId),
    onSuccess: (_data, experimentId) => {
      queryClient.invalidateQueries({ queryKey: ['experiment', experimentId] });
      queryClient.invalidateQueries({ queryKey: ['gameState', experimentId] });
    },
  });
}
