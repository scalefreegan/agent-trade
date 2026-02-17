import { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  useAgentDetail,
  useAgentStrategy,
  useAgentTransactions,
  useAgentDecisions,
} from '../api/agents';
import { usePerformance } from '../api/performance';
import { useExperiment } from '../api/experiments';
import { PortfolioBreakdown } from '../components/agent/PortfolioBreakdown';
import { PositionAllocationChart } from '../components/agent/PositionAllocationChart';
import { AgentPerformanceChart } from '../components/agent/AgentPerformanceChart';
import { StrategyPanel } from '../components/agent/StrategyPanel';
import { TransactionHistory } from '../components/agent/TransactionHistory';
import { DecisionLog } from '../components/agent/DecisionLog';
import { Badge, statusVariant } from '../components/ui/Badge';
import { Tabs } from '../components/ui/Tabs';

type Tab = 'portfolio' | 'performance' | 'strategy' | 'transactions' | 'decisions';

const TABS = [
  { id: 'portfolio' as Tab, label: 'Portfolio' },
  { id: 'performance' as Tab, label: 'Performance' },
  { id: 'strategy' as Tab, label: 'Strategy' },
  { id: 'transactions' as Tab, label: 'Transactions' },
  { id: 'decisions' as Tab, label: 'Decisions' },
];

export function AgentPage() {
  const { experimentId, agentId } = useParams<{ experimentId: string; agentId: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('portfolio');

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
        <div className="flex justify-between items-center mb-2">
          <h1 className="text-3xl font-bold text-foreground">{agent.name}</h1>
          <Badge variant={statusVariant(agent.status)} className="uppercase tracking-wide text-xs px-3 py-1">
            {agent.status}
          </Badge>
        </div>
        <div className="font-mono text-sm text-muted-foreground">{agent.agent_id}</div>
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
              <StrategyPanel strategy={strategy} />
            ) : (
              <div className="text-center py-12 text-muted-foreground">No strategy data available</div>
            )}
          </>
        )}

        {activeTab === 'transactions' && (
          <>
            {transactionsLoading ? (
              <div className="text-center py-12 text-muted-foreground">Loading transactions...</div>
            ) : transactions ? (
              <TransactionHistory history={transactions} />
            ) : (
              <div className="text-center py-12 text-muted-foreground">No transaction data available</div>
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
      </div>
    </div>
  );
}
