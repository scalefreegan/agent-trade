/**
 * Run controls for experiment execution.
 */

import { useState, useCallback } from 'react';
import { useStartRun, useRunStatus, usePauseExperiment, useResumeExperiment } from '../../api/runs';
import { useRunStream } from '../../hooks/useRunStream';
import { useQueryClient } from '@tanstack/react-query';
import { useExperiment } from '../../api/experiments';
import RunProgress from './RunProgress';

interface RunControlsProps {
  experimentId: string;
}

export default function RunControls({ experimentId }: RunControlsProps) {
  const queryClient = useQueryClient();
  const { data: experiment } = useExperiment(experimentId);
  const { data: runStatus } = useRunStatus(experimentId);
  const startRunMutation = useStartRun();
  const pauseMutation = usePauseExperiment();
  const resumeMutation = useResumeExperiment();
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Stable callbacks for useRunStream
  const onComplete = useCallback(() => {
    setIsStreaming(false);
    setError(null);
    queryClient.invalidateQueries();
  }, [queryClient]);

  const onError = useCallback((errorMsg: string) => {
    console.error('Run error:', errorMsg);
    setIsStreaming(false);
    setError(errorMsg);
    queryClient.invalidateQueries();
  }, [queryClient]);

  // Use run stream when a run is active
  const { events } = useRunStream(
    runStatus?.status === 'running' ? experimentId : null,
    { onComplete, onError }
  );

  const handleStartRun = async () => {
    try {
      setError(null);
      setIsStreaming(true);
      await startRunMutation.mutateAsync(experimentId);
    } catch (err) {
      console.error('Failed to start run:', err);
      setIsStreaming(false);
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to start run. Another run may be in progress.'
      );
    }
  };

  const handlePause = async () => {
    try {
      setError(null);
      await pauseMutation.mutateAsync(experimentId);
    } catch (err) {
      console.error('Failed to pause experiment:', err);
      setError(err instanceof Error ? err.message : 'Failed to pause experiment');
    }
  };

  const handleResume = async () => {
    try {
      setError(null);
      await resumeMutation.mutateAsync(experimentId);
    } catch (err) {
      console.error('Failed to resume experiment:', err);
      setError(err instanceof Error ? err.message : 'Failed to resume experiment');
    }
  };

  const isRunning = runStatus?.status === 'running' || isStreaming;
  const isPaused = experiment?.status === 'paused';
  const isCompleted = experiment?.status === 'completed';

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        {/* Run Day button */}
        <button
          onClick={handleStartRun}
          disabled={isRunning || isPaused || isCompleted || startRunMutation.isPending}
          className={`
            px-6 py-2 rounded-lg font-medium transition-colors
            ${
              isRunning || isPaused || isCompleted || startRunMutation.isPending
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-brand-700 text-white hover:bg-brand-600'
            }
          `}
          title={isPaused ? 'Resume the experiment to run' : isCompleted ? 'Experiment is completed' : undefined}
        >
          {isRunning ? 'Running...' : 'Run Day'}
        </button>

        {/* Pause button */}
        {!isPaused && !isCompleted && (
          <button
            onClick={handlePause}
            disabled={isRunning || pauseMutation.isPending}
            className={`
              px-6 py-2 rounded-lg font-medium transition-colors
              ${
                isRunning || pauseMutation.isPending
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-yellow-600 text-white hover:bg-yellow-500'
              }
            `}
          >
            {pauseMutation.isPending ? 'Pausing...' : 'Pause'}
          </button>
        )}

        {/* Resume button */}
        {isPaused && (
          <button
            onClick={handleResume}
            disabled={isRunning || resumeMutation.isPending}
            className={`
              px-6 py-2 rounded-lg font-medium transition-colors
              ${
                isRunning || resumeMutation.isPending
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-500'
              }
            `}
          >
            {resumeMutation.isPending ? 'Resuming...' : 'Resume'}
          </button>
        )}

        {/* Status badge */}
        {experiment && (
          <div className={`
            px-3 py-1 rounded-full text-xs font-medium
            ${experiment.status === 'active' ? 'bg-green-100 text-green-700' : ''}
            ${experiment.status === 'paused' ? 'bg-yellow-100 text-yellow-700' : ''}
            ${experiment.status === 'completed' ? 'bg-gray-100 text-gray-700' : ''}
          `}>
            {experiment.status}
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Run status error */}
      {runStatus?.error && !error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {runStatus.error}
        </div>
      )}

      {/* Show progress if running */}
      {isRunning && (
        <RunProgress events={events} />
      )}
    </div>
  );
}
