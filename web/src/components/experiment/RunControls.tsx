/**
 * Run controls for experiment execution.
 */

import { useState } from 'react';
import { useStartRun, useRunStatus } from '../../api/runs';
import { useRunStream } from '../../hooks/useRunStream';
import { useQueryClient } from '@tanstack/react-query';
import RunProgress from './RunProgress';

interface RunControlsProps {
  experimentId: string;
}

export default function RunControls({ experimentId }: RunControlsProps) {
  const queryClient = useQueryClient();
  const { data: runStatus } = useRunStatus(experimentId);
  const startRunMutation = useStartRun();
  const [isStreaming, setIsStreaming] = useState(false);

  // Use run stream when a run is active
  const { events } = useRunStream(
    runStatus?.status === 'running' ? experimentId : null,
    {
      onComplete: () => {
        setIsStreaming(false);
        // Invalidate all queries to refresh data
        queryClient.invalidateQueries();
      },
      onError: (error) => {
        console.error('Run error:', error);
        setIsStreaming(false);
        // Invalidate queries even on error
        queryClient.invalidateQueries();
      },
    }
  );

  const handleStartRun = async () => {
    try {
      setIsStreaming(true);
      await startRunMutation.mutateAsync(experimentId);
    } catch (error) {
      console.error('Failed to start run:', error);
      setIsStreaming(false);
      alert(
        error instanceof Error
          ? error.message
          : 'Failed to start run. Another run may be in progress.'
      );
    }
  };

  const isRunning = runStatus?.status === 'running' || isStreaming;
  const isDisabled = isRunning || startRunMutation.isPending;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <button
          onClick={handleStartRun}
          disabled={isDisabled}
          className={`
            px-6 py-2 rounded-lg font-medium transition-colors
            ${
              isDisabled
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-brand-700 text-white hover:bg-brand-600'
            }
          `}
        >
          {isRunning ? 'Running...' : 'Run Day'}
        </button>

        {runStatus && runStatus.status !== 'idle' && (
          <div className="text-sm text-gray-600">
            Status: <span className="font-medium">{runStatus.status}</span>
          </div>
        )}

        {runStatus?.error && (
          <div className="text-sm text-red-600">
            Error: {runStatus.error}
          </div>
        )}
      </div>

      {/* Show progress if running */}
      {isRunning && events.length > 0 && (
        <RunProgress events={events} />
      )}
    </div>
  );
}
