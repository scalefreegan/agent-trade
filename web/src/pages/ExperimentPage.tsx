import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useExperiment, useGameState } from '../api/experiments';
import { useLeaderboard, usePerformance } from '../api/performance';
import { Leaderboard } from '../components/experiment/Leaderboard';
import { PerformanceChart } from '../components/experiment/PerformanceChart';

type Tab = 'overview' | 'leaderboard' | 'performance';

export function ExperimentPage() {
  const { experimentId } = useParams<{ experimentId: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const { data: experiment, isLoading: expLoading, error: expError } = useExperiment(experimentId || '');
  const { data: gameState, isLoading: stateLoading, error: stateError } = useGameState(experimentId || '');
  const { data: leaderboard, isLoading: leaderboardLoading } = useLeaderboard(experimentId || '');
  const { data: performance, isLoading: performanceLoading } = usePerformance(experimentId || '');

  if (expLoading || stateLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading experiment...</div>
      </div>
    );
  }

  if (expError || stateError || !experiment || !gameState) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">
          {expError?.message || stateError?.message || 'Experiment not found'}
        </div>
      </div>
    );
  }

  // Build agent rankings for chart colors
  const agentRankings: Record<string, number> = {};
  if (leaderboard?.entries) {
    leaderboard.entries.forEach((entry) => {
      agentRankings[entry.agent_id] = entry.rank;
    });
  }

  const tabs = [
    { id: 'overview' as Tab, label: 'Overview' },
    { id: 'leaderboard' as Tab, label: 'Leaderboard' },
    { id: 'performance' as Tab, label: 'Performance' },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">{experiment.name}</h1>
        <p className="text-gray-600 mt-2">
          Trading Day {gameState.trading_day}
          {gameState.last_run && <> • Last run: {new Date(gameState.last_run).toLocaleDateString()}</>}
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm transition-colors
                ${
                  activeTab === tab.id
                    ? 'border-brand-700 text-brand-700'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <>
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Experiment Details</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-gray-600">Created</p>
                <p className="text-lg font-medium">{new Date(experiment.created_at).toLocaleDateString()}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Starting Capital</p>
                <p className="text-lg font-medium">${experiment.starting_capital.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Agents</p>
                <p className="text-lg font-medium">{experiment.num_agents}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Agents</h2>
            <div className="space-y-4">
              {gameState.agents.map((agent) => (
                <div key={agent.agent_id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-lg">{agent.name}</h3>
                    <span className="px-3 py-1 rounded-full text-xs font-medium bg-brand-600 text-white">
                      {agent.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600">Cash</p>
                      <p className="font-medium">${agent.portfolio.cash.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Positions</p>
                      <p className="font-medium">{Object.keys(agent.portfolio.positions).length}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {activeTab === 'leaderboard' && (
        <>
          {leaderboardLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-500">Loading leaderboard...</div>
            </div>
          ) : leaderboard?.entries ? (
            <Leaderboard entries={leaderboard.entries} />
          ) : (
            <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
              <div className="text-gray-500">No leaderboard data available</div>
            </div>
          )}
        </>
      )}

      {activeTab === 'performance' && (
        <>
          {performanceLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-500">Loading performance data...</div>
            </div>
          ) : performance?.data_points ? (
            <PerformanceChart
              dataPoints={performance.data_points}
              agentRankings={agentRankings}
              startingCapital={experiment.starting_capital}
            />
          ) : (
            <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
              <div className="text-gray-500">No performance data available</div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
