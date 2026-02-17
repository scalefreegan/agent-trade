/**
 * Hook for SSE (Server-Sent Events) stream of run progress with auto-reconnect and polling fallback.
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
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isTerminalRef = useRef(false);
  const isPollingRef = useRef(false);

  // Store callbacks in refs to avoid effect re-runs
  const callbacksRef = useRef(options);
  callbacksRef.current = options;

  useEffect(() => {
    if (!experimentId) {
      return;
    }

    // Reset state when starting new connection
    isTerminalRef.current = false;
    reconnectAttemptsRef.current = 0;
    isPollingRef.current = false;
    setEvents([]); // Clear events from previous runs

    const startPollingFallback = () => {
      if (isPollingRef.current || isTerminalRef.current) {
        return;
      }

      console.log('Starting polling fallback for run status');
      isPollingRef.current = true;

      const poll = async () => {
        if (isTerminalRef.current) {
          return;
        }

        try {
          const response = await fetch(`/api/v1/experiments/${experimentId}/run/status`);
          if (response.ok) {
            const status = await response.json();

            // Check if run completed or failed
            if (status.status === 'completed') {
              isTerminalRef.current = true;
              const completeEvent: RunEvent = {
                type: 'run_complete',
                timestamp: new Date().toISOString(),
                message: 'Run completed',
              };
              setEvents((prev) => [...prev, completeEvent]);
              if (callbacksRef.current.onComplete) {
                callbacksRef.current.onComplete();
              }
              if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
              }
            } else if (status.status === 'failed') {
              isTerminalRef.current = true;
              const errorEvent: RunEvent = {
                type: 'run_error',
                timestamp: new Date().toISOString(),
                error: status.error || 'Run failed',
              };
              setEvents((prev) => [...prev, errorEvent]);
              if (callbacksRef.current.onError) {
                callbacksRef.current.onError(status.error || 'Run failed');
              }
              if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
              }
            }
          }
        } catch (error) {
          console.error('Polling error:', error);
        }
      };

      // Poll every 2 seconds
      pollIntervalRef.current = setInterval(poll, 2000);
      poll(); // Initial poll
    };

    const connect = () => {
      // Don't reconnect if we've seen a terminal event or are polling
      if (isTerminalRef.current || isPollingRef.current) {
        return;
      }

      // Create EventSource for SSE
      const eventSource = new EventSource(`/api/v1/experiments/${experimentId}/run/stream`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const data: RunEvent = JSON.parse(event.data);

          setEvents((prev) => [...prev, data]);

          // Call event callback
          if (callbacksRef.current.onEvent) {
            callbacksRef.current.onEvent(data);
          }

          // Handle completion
          if (data.type === 'run_complete') {
            isTerminalRef.current = true;
            if (callbacksRef.current.onComplete) {
              callbacksRef.current.onComplete();
            }
            eventSource.close();
            setIsConnected(false);
          }

          // Handle error
          if (data.type === 'run_error') {
            isTerminalRef.current = true;
            if (callbacksRef.current.onError) {
              callbacksRef.current.onError(data.error || 'Unknown error');
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

        // Don't retry if we've seen a terminal event
        if (isTerminalRef.current) {
          return;
        }

        // Implement exponential backoff for reconnection
        const maxAttempts = 5;
        if (reconnectAttemptsRef.current < maxAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxAttempts})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        } else {
          // Fall back to polling after max SSE attempts
          console.log('SSE retry exhausted, falling back to polling');
          startPollingFallback();
        }
      };
    };

    connect();

    // Cleanup on unmount
    return () => {
      isTerminalRef.current = true;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      setIsConnected(false);
    };
  }, [experimentId]); // Only depend on experimentId

  const disconnect = () => {
    isTerminalRef.current = true;
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      setIsConnected(false);
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
  };

  return {
    isConnected,
    events,
    disconnect,
  };
}
