import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useExperiment, useGameState } from '../api/experiments';
import { useLeaderboard, usePerformance } from '../api/performance';
import { useTaxMetrics, useHoldingPeriods, useExperimentReport } from '../api/analysis';
import { Leaderboard } from '../components/experiment/Leaderboard';
import { PerformanceChart } from '../components/experiment/PerformanceChart';
import { TaxImpactChart } from '../components/analysis/TaxImpactChart';
import { HoldingPeriodChart } from '../components/analysis/HoldingPeriodChart';
import { ExperimentReportView } from '../components/analysis/ExperimentReport';
import RunControls from '../components/experiment/RunControls';

type Tab = 'overview' | 'leaderboard' | 'performance' | 'analysis';

export function ExperimentPage() {
  const { experimentId } = useParams<{ experimentId: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const { data: experiment, isLoading: expLoading, error: expError } = useExperiment(experimentId || '');
  const { data: gameState, isLoading: stateLoading, error: stateError } = useGameState(experimentId || '');
  const { data: leaderboard, isLoading: leaderboardLoading } = useLeaderboard(experimentId || '');
  const { data: performance, isLoading: performanceLoading } = usePerformance(experimentId || '');
  const { data: taxMetrics, isLoading: taxMetricsLoading, error: taxMetricsError } = useTaxMetrics(experimentId || '');
  const { data: holdingPeriods, isLoading: holdingPeriodsLoading, error: holdingPeriodsError } = useHoldingPeriods(experimentId || '');
  const { data: experimentReport, isLoading: reportLoading, error: reportError } = useExperimentReport(experimentId || '');

  if (expLoading || stateLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading experiment...</div>
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

  // Build agent names mapping for analysis charts
  const agentNames: Record<string, string> = {};
  if (gameState?.agents) {
    gameState.agents.forEach((agent) => {
      agentNames[agent.agent_id] = agent.name;
    });
  }

  const tabs = [
    { id: 'overview' as Tab, label: 'Overview' },
    { id: 'leaderboard' as Tab, label: 'Leaderboard' },
    { id: 'performance' as Tab, label: 'Performance' },
    { id: 'analysis' as Tab, label: 'Analysis' },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">{experiment.name}</h1>
            <p className="text-muted-foreground mt-2">
              Trading Day {gameState.trading_day}
              {gameState.last_run && <> • Last run: {new Date(gameState.last_run).toLocaleDateString()}</>}
            </p>
          </div>
          <div>
            <RunControls experimentId={experimentId!} />
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-border mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm transition-colors
                ${
                  activeTab === tab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
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
          <div className="bg-card text-card-foreground rounded-xl border border-border shadow-card p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4 text-foreground">Experiment Details</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-muted-foreground">Created</p>
                <p className="text-lg font-medium text-foreground">{new Date(experiment.created_at).toLocaleDateString()}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Starting Capital</p>
                <p className="text-lg font-medium text-foreground">${experiment.starting_capital.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Agents</p>
                <p className="text-lg font-medium text-foreground">{experiment.num_agents}</p>
              </div>
            </div>
          </div>

          <div className="bg-card text-card-foreground rounded-xl border border-border shadow-card p-6">
            <h2 className="text-xl font-semibold mb-4 text-foreground">Agents</h2>
            <div className="space-y-4">
              {gameState.agents.map((agent) => (
                <Link
                  key={agent.agent_id}
                  to={`/experiments/${experimentId}/agents/${agent.agent_id}`}
                  className="block border border-border rounded-lg p-4 hover:border-primary hover:shadow-md transition-all"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-lg text-foreground">
                      {agent.name}
                    </h3>
                    <span className="px-3 py-1 rounded-full text-xs font-medium bg-primary text-primary-foreground">
                      {agent.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Cash</p>
                      <p className="font-medium text-foreground">${agent.portfolio.cash.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Positions</p>
                      <p className="font-medium text-foreground">{Object.keys(agent.portfolio.positions).length}</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </>
      )}

      {activeTab === 'leaderboard' && (
        <>
          {leaderboardLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-muted-foreground">Loading leaderboard...</div>
            </div>
          ) : leaderboard?.entries ? (
            <Leaderboard entries={leaderboard.entries} />
          ) : (
            <div className="flex items-center justify-center h-64 bg-muted rounded-xl">
              <div className="text-muted-foreground">No leaderboard data available</div>
            </div>
          )}
        </>
      )}

      {activeTab === 'performance' && (
        <>
          {performanceLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-muted-foreground">Loading performance data...</div>
            </div>
          ) : performance?.data_points ? (
            <PerformanceChart
              dataPoints={performance.data_points}
              agentRankings={agentRankings}
              startingCapital={experiment.starting_capital}
            />
          ) : (
            <div className="flex items-center justify-center h-64 bg-muted rounded-xl">
              <div className="text-muted-foreground">No performance data available</div>
            </div>
          )}
        </>
      )}

      {activeTab === 'analysis' && (
        <>
          {taxMetricsLoading || holdingPeriodsLoading || reportLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-muted-foreground">Loading analysis data...</div>
            </div>
          ) : (
            <div className="space-y-6">
              {taxMetricsError ? (
                <div className="flex items-center justify-center h-32 bg-red-50 dark:bg-red-950/20 rounded-xl border border-red-200 dark:border-red-900">
                  <div className="text-red-600 dark:text-red-400">Failed to load tax metrics: {taxMetricsError.message}</div>
                </div>
              ) : taxMetrics && Object.keys(taxMetrics).length > 0 ? (
                <TaxImpactChart taxMetrics={taxMetrics} agentNames={agentNames} />
              ) : (
                <div className="flex items-center justify-center h-32 bg-muted rounded-xl">
                  <div className="text-muted-foreground">No tax data available — complete some sell transactions</div>
                </div>
              )}

              {holdingPeriodsError ? (
                <div className="flex items-center justify-center h-32 bg-red-50 dark:bg-red-950/20 rounded-xl border border-red-200 dark:border-red-900">
                  <div className="text-red-600 dark:text-red-400">Failed to load holding periods: {holdingPeriodsError.message}</div>
                </div>
              ) : holdingPeriods && Object.keys(holdingPeriods).length > 0 ? (
                <HoldingPeriodChart holdingPeriods={holdingPeriods} agentNames={agentNames} />
              ) : (
                <div className="flex items-center justify-center h-32 bg-muted rounded-xl">
                  <div className="text-muted-foreground">No holding period data available — complete some sell transactions</div>
                </div>
              )}

              {reportError ? (
                <div className="flex items-center justify-center h-32 bg-red-50 dark:bg-red-950/20 rounded-xl border border-red-200 dark:border-red-900">
                  <div className="text-red-600 dark:text-red-400">Failed to load report: {reportError.message}</div>
                </div>
              ) : experimentReport ? (
                <ExperimentReportView report={experimentReport} />
              ) : null}
            </div>
          )}
        </>
      )}
    </div>
  );
}
