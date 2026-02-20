/**
 * API hooks for the Agent Advisor feature.
 */
import { useMutation, useQuery } from '@tanstack/react-query';
import { fetchApi, postApi } from './client';
import type {
  AdvisorJobStatus,
  AdvisorPresetsResponse,
  AdvisorRequest,
  ExperimentAgentInfo,
} from './types';

export function useAdvisorPresets() {
  return useQuery({
    queryKey: ['advisorPresets'],
    queryFn: () => fetchApi<AdvisorPresetsResponse>('/advisor/presets'),
    staleTime: 5 * 60 * 1000, // presets rarely change
  });
}

export function useStartRecommendation() {
  return useMutation({
    mutationFn: (data: AdvisorRequest) =>
      postApi<AdvisorJobStatus>('/advisor/recommend', data),
  });
}

export function useAdvisorJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['advisorJob', jobId],
    queryFn: () => fetchApi<AdvisorJobStatus>(`/advisor/jobs/${jobId}`),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' || status === 'pending' ? 2000 : false;
    },
  });
}

export function useExperimentAgents(experimentId: string | null) {
  return useQuery({
    queryKey: ['experimentAgents', experimentId],
    queryFn: () =>
      fetchApi<ExperimentAgentInfo[]>(
        `/advisor/experiments/${experimentId}/agents`
      ),
    enabled: !!experimentId,
  });
}
