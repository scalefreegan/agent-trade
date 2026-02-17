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
import { Card } from '../components/ui/Card';
import { Tabs } from '../components/ui/Tabs';
import { Badge, statusVariant } from '../components/ui/Badge';
import { MetricCard } from '../components/ui/MetricCard';

type Tab = 'overview' | 'leaderboard' | 'performance' | 'analysis';

export function ExperimentPage() {
  const { experimentId } = useParams<{ experimentId: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const { data: experiment, isLoading: expLoading, error: expError } = useExperiment(experimentId || '');
  const { data: gameState, isLoading: stateLoading, error: stateError } = useGameState(experimentId || '');
  const { data: leaderboard, isLoading: leaderboardLoading, error: leaderboardError } = useLeaderboard(experimentId || '');
  const { data: performance, isLoading: performanceLoading, error: performanceError } = usePerformance(experimentId || '');
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
        <div className="text-loss">
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
      <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} className="mb-6" />

      {/* Tab panels — always mounted so aria-controls always resolves; inactive panels hidden */}
      <div role="tabpanel" id="panel-overview" aria-labelledby="tab-overview" hidden={activeTab !== 'overview'}>
        <Card className="mb-6">
          <h2 className="text-xl font-semibold mb-4 text-foreground">Experiment Details</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            <MetricCard
              label="Created"
              value={new Date(experiment.created_at).toLocaleDateString()}
            />
            <MetricCard
              label="Starting Capital"
              value={`$${experiment.starting_capital.toLocaleString()}`}
            />
            <MetricCard label="Agents" value={experiment.num_agents} />
          </div>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold mb-4 text-foreground">Agents</h2>
          <div className="space-y-4">
            {gameState.agents.map((agent) => (
              <Link
                key={agent.agent_id}
                to={`/experiments/${experimentId}/agents/${agent.agent_id}`}
                className="block border border-border rounded-lg p-4 hover:border-primary hover:shadow-md transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-lg text-foreground">{agent.name}</h3>
                  <Badge variant={statusVariant(agent.status)}>{agent.status}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <MetricCard label="Cash" value={`$${agent.portfolio.cash.toLocaleString()}`} />
                  <MetricCard label="Positions" value={Object.keys(agent.portfolio.positions).length} />
                </div>
              </Link>
            ))}
          </div>
        </Card>
      </div>

      <div role="tabpanel" id="panel-leaderboard" aria-labelledby="tab-leaderboard" hidden={activeTab !== 'leaderboard'}>
        {leaderboardLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-muted-foreground">Loading leaderboard...</div>
          </div>
        ) : leaderboardError ? (
          <div className="flex items-center justify-center h-64 bg-loss/10 rounded-xl border border-loss/30">
            <div className="text-loss">Failed to load leaderboard: {leaderboardError.message}</div>
          </div>
        ) : leaderboard?.entries ? (
          <Leaderboard entries={leaderboard.entries} />
        ) : (
          <div className="flex items-center justify-center h-64 bg-muted rounded-xl">
            <div className="text-muted-foreground">No leaderboard data available</div>
          </div>
        )}
      </div>

      <div role="tabpanel" id="panel-performance" aria-labelledby="tab-performance" hidden={activeTab !== 'performance'}>
        {performanceLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-muted-foreground">Loading performance data...</div>
          </div>
        ) : performanceError ? (
          <div className="flex items-center justify-center h-64 bg-loss/10 rounded-xl border border-loss/30">
            <div className="text-loss">Failed to load performance data: {performanceError.message}</div>
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
      </div>

      <div role="tabpanel" id="panel-analysis" aria-labelledby="tab-analysis" hidden={activeTab !== 'analysis'}>
        {taxMetricsLoading || holdingPeriodsLoading || reportLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-muted-foreground">Loading analysis data...</div>
          </div>
        ) : (
          <div className="space-y-6">
            {taxMetricsError ? (
              <div className="flex items-center justify-center h-32 bg-loss/10 rounded-xl border border-loss/30">
                <div className="text-loss">Failed to load tax metrics: {taxMetricsError.message}</div>
              </div>
            ) : taxMetrics && Object.keys(taxMetrics).length > 0 ? (
              <TaxImpactChart taxMetrics={taxMetrics} agentNames={agentNames} />
            ) : (
              <div className="flex items-center justify-center h-32 bg-muted rounded-xl">
                <div className="text-muted-foreground">No tax data available — complete some sell transactions</div>
              </div>
            )}

            {holdingPeriodsError ? (
              <div className="flex items-center justify-center h-32 bg-loss/10 rounded-xl border border-loss/30">
                <div className="text-loss">Failed to load holding periods: {holdingPeriodsError.message}</div>
              </div>
            ) : holdingPeriods && Object.keys(holdingPeriods).length > 0 ? (
              <HoldingPeriodChart holdingPeriods={holdingPeriods} agentNames={agentNames} />
            ) : (
              <div className="flex items-center justify-center h-32 bg-muted rounded-xl">
                <div className="text-muted-foreground">No holding period data available — complete some sell transactions</div>
              </div>
            )}

            {reportError ? (
              <div className="flex items-center justify-center h-32 bg-loss/10 rounded-xl border border-loss/30">
                <div className="text-loss">Failed to load report: {reportError.message}</div>
              </div>
            ) : experimentReport ? (
              <ExperimentReportView report={experimentReport} />
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
