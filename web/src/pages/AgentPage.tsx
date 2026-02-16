import { useParams } from 'react-router-dom';

export function AgentPage() {
  const { experimentId, agentId } = useParams<{ experimentId: string; agentId: string }>();

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Agent Detail</h1>
        <p className="text-gray-600 mt-2">
          Agent: {agentId} • Experiment: {experimentId}
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg font-medium mb-2">
            Agent detail view coming in Phase 3
          </p>
          <p className="text-sm text-gray-400">
            This page will show portfolio breakdown, strategy, transactions, and decision history
          </p>
        </div>
      </div>
    </div>
  );
}
