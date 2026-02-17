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
      // No job found - return idle status
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
