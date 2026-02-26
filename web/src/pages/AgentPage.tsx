import { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  useAgentDetail,
  useAgentStrategy,
  useAgentTransactions,
  useAgentDecisions,
  useAgentHoldings,
  useAgentAlerts,
  useAgentBenchmarks,
  useUpdateAgent,
  useUpdateStrategy,
  useUpdateGuidance,
} from '../api/agents';
import { usePerformance } from '../api/performance';
import { useExperiment } from '../api/experiments';
import { PortfolioBreakdown } from '../components/agent/PortfolioBreakdown';
import { PositionAllocationChart } from '../components/agent/PositionAllocationChart';
import { AgentPerformanceChart } from '../components/agent/AgentPerformanceChart';
import { StrategyPanel } from '../components/agent/StrategyPanel';
import { StrategyEditModal } from '../components/agent/StrategyEditModal';
import { DecisionLog } from '../components/agent/DecisionLog';
import { HoldingsInfo } from '../components/agent/HoldingsInfo';
import { AlertsPanel } from '../components/agent/AlertsPanel';
import { TransactionList } from '../components/agent/TransactionList';
import { Badge, statusVariant } from '../components/ui/Badge';
import { InlineEdit } from '../components/ui/InlineEdit';
import { Tabs } from '../components/ui/Tabs';

type Tab = 'portfolio' | 'history' | 'info' | 'performance' | 'strategy' | 'decisions' | 'alerts';

const TABS = [
  { id: 'portfolio' as Tab, label: 'Portfolio' },
  { id: 'history' as Tab, label: 'History' },
  { id: 'info' as Tab, label: 'Info' },
  { id: 'performance' as Tab, label: 'Performance' },
  { id: 'strategy' as Tab, label: 'Strategy' },
  { id: 'decisions' as Tab, label: 'Decisions' },
  { id: 'alerts' as Tab, label: 'Alerts' },
];

export function AgentPage() {
  const { experimentId, agentId } = useParams<{ experimentId: string; agentId: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('portfolio');
  const [strategyEditOpen, setStrategyEditOpen] = useState(false);

  const { data: experiment } = useExperiment(experimentId || '');
  const { data: agent, isLoading: agentLoading, error: agentError } = useAgentDetail(
    experimentId || '',
    agentId || ''
  );
  const { data: strategy, isLoading: strategyLoading } = useAgentStrategy(
    experimentId || '',
    agentId || ''
  );
  const { data: transactions, isLoading: transactionsLoading } = useAgentTransactions(
    experimentId || '',
    agentId || ''
  );
  const { data: decisions, isLoading: decisionsLoading } = useAgentDecisions(
    experimentId || '',
    agentId || ''
  );
  const { data: performance, isLoading: performanceLoading } = usePerformance(
    experimentId || ''
  );
  const { data: holdings, isLoading: holdingsLoading } = useAgentHoldings(
    experimentId || '',
    agentId || ''
  );
  const { data: alerts, isLoading: alertsLoading } = useAgentAlerts(
    experimentId || '',
    agentId || ''
  );
  const { data: benchmarks } = useAgentBenchmarks(
    experimentId || '',
    agentId || ''
  );
  const updateAgent = useUpdateAgent(experimentId || '', agentId || '');
  const updateStrategy = useUpdateStrategy(experimentId || '', agentId || '');
  const updateGuidance = useUpdateGuidance(experimentId || '', agentId || '');

  if (agentLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading agent...</div>
      </div>
    );
  }

  if (agentError || !agent) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-loss">
          {agentError?.message || 'Agent not found'}
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Agent Header */}
      <div className="mb-8 pb-6 border-b-2 border-border">
        <div className="flex justify-between items-start mb-2">
          <InlineEdit
            value={agent.name}
            onSave={(name) => updateAgent.mutate({ name })}
            isPending={updateAgent.isPending}
            className="text-3xl font-bold text-foreground"
            inputClassName="text-3xl font-bold"
          />
          <Badge variant={statusVariant(agent.status)} className="uppercase tracking-wide text-xs px-3 py-1 flex-shrink-0 ml-4">
            {agent.status}
          </Badge>
        </div>
        <div className="font-mono text-sm text-muted-foreground mb-1">{agent.agent_id}</div>
        <InlineEdit
          value={agent.description ?? ''}
          onSave={(description) => updateAgent.mutate({ description })}
          isPending={updateAgent.isPending}
          emptyText="Add description..."
          placeholder="Add a description for this agent"
          multiline
          className="text-sm text-muted-foreground"
          inputClassName="text-sm"
        />
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} className="mb-8" />

      {/* Tab Content */}
      <div className="animate-fade-in">
        {activeTab === 'portfolio' && (
          <div>
            <div className="mb-8">
              <PositionAllocationChart portfolio={agent.portfolio} />
            </div>
            <PortfolioBreakdown portfolio={agent.portfolio} metrics={agent.metrics} />
          </div>
        )}

        {activeTab === 'history' && (
          <>
            {transactionsLoading ? (
              <div className="text-center py-12 text-muted-foreground">Loading history...</div>
            ) : transactions ? (
              <TransactionList transactions={transactions} />
            ) : (
              <div className="text-center py-12 text-muted-foreground">No transaction history available</div>
            )}
          </>
        )}

        {activeTab === 'info' && (
          <>
            {holdingsLoading ? (
              <div className="text-center py-12 text-muted-foreground">Loading holdings info...</div>
            ) : holdings ? (
              <HoldingsInfo data={holdings} />
            ) : (
              <div className="text-center py-12 text-muted-foreground">No holdings data available</div>
            )}
          </>
        )}

        {activeTab === 'performance' && (
          <>
            {performanceLoading ? (
              <div className="text-center py-12 text-muted-foreground">Loading performance data...</div>
            ) : performance?.data_points && experiment ? (
              <AgentPerformanceChart
                dataPoints={performance.data_points}
                agentId={agent.agent_id}
                agentName={agent.name}
                startingCapital={experiment.starting_capital}
                benchmarks={benchmarks?.benchmarks}
              />
            ) : (
              <div className="text-center py-12 text-muted-foreground">No performance data available</div>
            )}
          </>
        )}

        {activeTab === 'strategy' && (
          <>
            {strategyLoading ? (
              <div className="text-center py-12 text-muted-foreground">Loading strategy...</div>
            ) : strategy ? (
              <>
                <StrategyPanel
                  strategy={strategy}
                  guidance={agent.guidance}
                  onEditStrategy={() => setStrategyEditOpen(true)}
                  onSaveGuidance={(g) =>
                    new Promise<void>((resolve, reject) =>
                      updateGuidance.mutate(g, { onSuccess: () => resolve(), onError: (e) => reject(e) })
                    )
                  }
                  isGuidancePending={updateGuidance.isPending}
                  guidanceError={updateGuidance.error?.message ?? null}
                />
                <StrategyEditModal
                  open={strategyEditOpen}
                  strategy={strategy}
                  onClose={() => { setStrategyEditOpen(false); updateStrategy.reset(); }}
                  onSave={(data) => updateStrategy.mutate(data, { onSuccess: () => setStrategyEditOpen(false) })}
                  isPending={updateStrategy.isPending}
                  error={updateStrategy.error?.message ?? null}
                />
              </>
            ) : (
              <div className="text-center py-12 text-muted-foreground">No strategy data available</div>
            )}
          </>
        )}

        {activeTab === 'decisions' && (
          <>
            {decisionsLoading ? (
              <div className="text-center py-12 text-muted-foreground">Loading decisions...</div>
            ) : decisions ? (
              <DecisionLog
                experimentId={experimentId || ''}
                agentId={agentId || ''}
                decisions={decisions}
              />
            ) : (
              <div className="text-center py-12 text-muted-foreground">No decision data available</div>
            )}
          </>
        )}

        {activeTab === 'alerts' && (
          <>
            {alertsLoading ? (
              <div className="text-center py-12 text-muted-foreground">Loading alerts...</div>
            ) : alerts ? (
              <AlertsPanel data={alerts} />
            ) : (
              <div className="text-center py-12 text-muted-foreground">No alerts data available</div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
