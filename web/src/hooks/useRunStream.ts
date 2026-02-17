/**
 * Hook for SSE (Server-Sent Events) stream of run progress.
 */

import { useEffect, useRef, useState } from 'react';

export interface RunEvent {
  type: 'connected' | 'agent_start' | 'agent_complete' | 'agent_error' | 'run_complete' | 'run_error';
  timestamp?: string;
  agent_id?: string;
  message?: string;
  error?: string;
  experiment_id?: string;
}

export interface UseRunStreamOptions {
  onEvent?: (event: RunEvent) => void;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export function useRunStream(experimentId: string | null, options: UseRunStreamOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!experimentId) {
      return;
    }

    // Create EventSource for SSE
    const eventSource = new EventSource(`/api/v1/experiments/${experimentId}/run/stream`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const data: RunEvent = JSON.parse(event.data);

        setEvents((prev) => [...prev, data]);

        // Call event callback
        if (options.onEvent) {
          options.onEvent(data);
        }

        // Handle completion
        if (data.type === 'run_complete') {
          if (options.onComplete) {
            options.onComplete();
          }
          eventSource.close();
          setIsConnected(false);
        }

        // Handle error
        if (data.type === 'run_error') {
          if (options.onError) {
            options.onError(data.error || 'Unknown error');
          }
          eventSource.close();
          setIsConnected(false);
        }
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      setIsConnected(false);
      eventSource.close();

      if (options.onError) {
        options.onError('Connection lost');
      }
    };

    // Cleanup on unmount
    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [experimentId, options]);

  const disconnect = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      setIsConnected(false);
    }
  };

  return {
    isConnected,
    events,
    disconnect,
  };
}
