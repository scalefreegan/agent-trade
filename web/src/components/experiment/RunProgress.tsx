/**
 * Run progress indicators showing per-agent status.
 */

import { useMemo } from 'react';
import type { RunEvent } from '../../hooks/useRunStream';
import { Card } from '../ui/Card';
import { Badge, statusVariant } from '../ui/Badge';

interface RunProgressProps {
  events: RunEvent[];
}

interface AgentProgress {
  agent_id: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  message?: string;
  error?: string;
}

export default function RunProgress({ events }: RunProgressProps) {
  const agents = useMemo(() => {
    const agentProgress = new Map<string, AgentProgress>();

    for (const event of events) {
      if (!event.agent_id) continue;

      switch (event.type) {
        case 'agent_start':
          agentProgress.set(event.agent_id, {
            agent_id: event.agent_id,
            status: 'running',
            message: event.message,
          });
          break;

        case 'agent_complete':
          agentProgress.set(event.agent_id, {
            agent_id: event.agent_id,
            status: 'complete',
            message: event.message,
          });
          break;

        case 'agent_error':
          agentProgress.set(event.agent_id, {
            agent_id: event.agent_id,
            status: 'error',
            error: event.error,
            message: event.message,
          });
          break;
      }
    }

    return Array.from(agentProgress.values());
  }, [events]);

  if (agents.length === 0) {
    return (
      <Card className="bg-muted/40">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Spinner />
          <span>Starting agents...</span>
        </div>
      </Card>
    );
  }

  return (
    <Card className="bg-muted/40">
      <h3 className="text-sm font-medium text-foreground mb-3">Agent Progress</h3>
      <div className="space-y-2" aria-live="polite">
        {agents.map((agent) => (
          <div key={agent.agent_id} className="flex items-center gap-3">
            <div className="flex-shrink-0">
              {agent.status === 'running' && <Spinner />}
              {agent.status === 'complete' && <Checkmark />}
              {agent.status === 'error' && <ErrorIcon />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-foreground truncate">{agent.agent_id}</div>
              {agent.message && (
                <div className="text-xs text-muted-foreground truncate">{agent.message}</div>
              )}
              {agent.error && (
                <div className="text-xs text-loss truncate">{agent.error}</div>
              )}
            </div>
            <div className="flex-shrink-0">
              <Badge variant={statusVariant(agent.status)}>{agent.status}</Badge>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Spinner() {
  return (
    <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
  );
}

function Checkmark() {
  return (
    <div className="w-5 h-5 bg-gain rounded-full flex items-center justify-center">
      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    </div>
  );
}

function ErrorIcon() {
  return (
    <div className="w-5 h-5 bg-loss rounded-full flex items-center justify-center">
      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    </div>
  );
}
