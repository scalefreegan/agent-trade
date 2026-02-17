/**
 * Run progress indicators showing per-agent status.
 */

import { RunEvent } from '../../hooks/useRunStream';

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
  // Build agent progress map from events
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

  const agents = Array.from(agentProgress.values());

  if (agents.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center gap-2 text-gray-600">
          <Spinner />
          <span>Starting agents...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-3">Agent Progress</h3>

      <div className="space-y-2">
        {agents.map((agent) => (
          <div key={agent.agent_id} className="flex items-center gap-3">
            {/* Status indicator */}
            <div className="flex-shrink-0">
              {agent.status === 'running' && <Spinner />}
              {agent.status === 'complete' && <Checkmark />}
              {agent.status === 'error' && <ErrorIcon />}
            </div>

            {/* Agent ID */}
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 truncate">
                {agent.agent_id}
              </div>
              {agent.message && (
                <div className="text-xs text-gray-500 truncate">
                  {agent.message}
                </div>
              )}
              {agent.error && (
                <div className="text-xs text-red-600 truncate">
                  {agent.error}
                </div>
              )}
            </div>

            {/* Status badge */}
            <div className="flex-shrink-0">
              <StatusBadge status={agent.status} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <div className="w-5 h-5 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
  );
}

function Checkmark() {
  return (
    <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    </div>
  );
}

function ErrorIcon() {
  return (
    <div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    </div>
  );
}

function StatusBadge({ status }: { status: AgentProgress['status'] }) {
  const colors = {
    pending: 'bg-gray-100 text-gray-700',
    running: 'bg-blue-100 text-blue-700',
    complete: 'bg-green-100 text-green-700',
    error: 'bg-red-100 text-red-700',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded ${colors[status]}`}>
      {status}
    </span>
  );
}
