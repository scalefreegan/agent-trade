/**
 * Run controls for experiment execution.
 */

import { useState, useCallback } from 'react';
import { useStartRun, useRunStatus, usePauseExperiment, useResumeExperiment } from '../../api/runs';
import { useRunStream } from '../../hooks/useRunStream';
import { useQueryClient } from '@tanstack/react-query';
import { useExperiment } from '../../api/experiments';
import RunProgress from './RunProgress';
import { Badge, statusVariant } from '../ui/Badge';
import { ErrorBoundary } from '../ui/ErrorBoundary';

interface RunControlsProps {
  experimentId: string;
}

export default function RunControls({ experimentId }: RunControlsProps) {
  const queryClient = useQueryClient();
  const { data: experiment } = useExperiment(experimentId);
  const { data: runStatus, isLoading: runStatusLoading } = useRunStatus(experimentId);
  const startRunMutation = useStartRun();
  const pauseMutation = usePauseExperiment();
  const resumeMutation = useResumeExperiment();
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const isRunning = runStatus?.status === 'running' || isStreaming || runStatusLoading;
  const isPaused = experiment?.status === 'paused';
  const isCompleted = experiment?.status === 'completed';

  const disabledBtn = 'px-6 py-2 rounded-lg font-medium bg-muted text-muted-foreground cursor-not-allowed';
  const primaryBtn = 'px-6 py-2 rounded-lg font-medium bg-primary text-primary-foreground hover:opacity-90 transition-opacity';
  const warningBtn = 'px-6 py-2 rounded-lg font-medium bg-warning text-warning-foreground hover:opacity-90 transition-opacity';
  const gainBtn = 'px-6 py-2 rounded-lg font-medium bg-gain text-white hover:opacity-90 transition-opacity';

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleStartRun}
          disabled={isRunning || isPaused || isCompleted || startRunMutation.isPending}
          className={isRunning || isPaused || isCompleted || startRunMutation.isPending ? disabledBtn : primaryBtn}
          title={isPaused ? 'Resume the experiment to run' : isCompleted ? 'Experiment is completed' : undefined}
        >
          {isRunning ? 'Running...' : 'Run Day'}
        </button>

        {!isPaused && !isCompleted && (
          <button
            type="button"
            onClick={handlePause}
            disabled={isRunning || pauseMutation.isPending}
            className={isRunning || pauseMutation.isPending ? disabledBtn : warningBtn}
          >
            {pauseMutation.isPending ? 'Pausing...' : 'Pause'}
          </button>
        )}

        {isPaused && (
          <button
            type="button"
            onClick={handleResume}
            disabled={isRunning || resumeMutation.isPending}
            className={isRunning || resumeMutation.isPending ? disabledBtn : gainBtn}
          >
            {resumeMutation.isPending ? 'Resuming...' : 'Resume'}
          </button>
        )}

        {experiment && (
          <Badge variant={statusVariant(experiment.status)}>{experiment.status}</Badge>
        )}
      </div>

      {error && (
        <div role="alert" className="bg-loss/10 border border-loss/30 rounded-lg p-3 text-sm text-loss">
          {error}
        </div>
      )}

      {runStatus?.error && !error && (
        <div role="alert" className="bg-loss/10 border border-loss/30 rounded-lg p-3 text-sm text-loss">
          {runStatus.error}
        </div>
      )}

      {isRunning && (
        <ErrorBoundary fallback={(err, reset) => (
          <div className="bg-loss/10 border border-loss/30 rounded-lg p-3 text-sm text-loss">
            <p>Run progress display error: {err.message}</p>
            <button onClick={reset} className="mt-2 underline text-xs">Try again</button>
          </div>
        )}>
          <RunProgress events={events} />
        </ErrorBoundary>
      )}
    </div>
  );
}
