/**
 * API functions for run control.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export interface RunStatus {
  job_id: string;
  experiment_id: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  error?: string;
}

/**
 * Start a run for an experiment.
 */
export async function startRun(experimentId: string): Promise<RunStatus> {
  const response = await fetch(`/api/v1/experiments/${experimentId}/run`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }

  return response.json();
}

/**
 * Get run status for an experiment.
 */
export async function getRunStatus(experimentId: string): Promise<RunStatus> {
  const response = await fetch(`/api/v1/experiments/${experimentId}/run/status`);

  if (!response.ok) {
    if (response.status === 404) {
      // 404 could mean either "no job" or "experiment not found"
      // Verify the experiment exists before returning idle status
      const expResponse = await fetch(`/api/v1/experiments/${experimentId}`);
      if (!expResponse.ok) {
        // Experiment doesn't exist
        throw new Error('Experiment not found');
      }

      // Experiment exists, just no job - return idle status
      return {
        job_id: '',
        experiment_id: experimentId,
        status: 'idle',
        started_at: '',
      };
    }
    const error = await response.text();
    throw new Error(error);
  }

  return response.json();
}

/**
 * Hook to get run status.
 */
export function useRunStatus(experimentId: string | null) {
  return useQuery({
    queryKey: ['runStatus', experimentId],
    queryFn: () => getRunStatus(experimentId!),
    enabled: !!experimentId,
    refetchInterval: (data) => {
      // Poll every 2 seconds if running
      return data?.status === 'running' ? 2000 : false;
    },
  });
}

/**
 * Hook to start a run.
 */
export function useStartRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: startRun,
    onSuccess: (data) => {
      // Invalidate run status
      queryClient.invalidateQueries({ queryKey: ['runStatus', data.experiment_id] });
    },
  });
}

/**
 * Pause an experiment.
 */
export async function pauseExperiment(experimentId: string): Promise<{ status: string; new_status: string }> {
  const response = await fetch(`/api/v1/experiments/${experimentId}/pause`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }

  return response.json();
}

/**
 * Resume an experiment.
 */
export async function resumeExperiment(experimentId: string): Promise<{ status: string; new_status: string }> {
  const response = await fetch(`/api/v1/experiments/${experimentId}/resume`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error);
  }

  return response.json();
}

/**
 * Hook to pause an experiment.
 */
export function usePauseExperiment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: pauseExperiment,
    onSuccess: (data, experimentId) => {
      // Invalidate experiment data
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
    mutationFn: resumeExperiment,
    onSuccess: (data, experimentId) => {
      // Invalidate experiment data
      queryClient.invalidateQueries({ queryKey: ['experiment', experimentId] });
      queryClient.invalidateQueries({ queryKey: ['gameState', experimentId] });
    },
  });
}
