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

type Tab = 'portfolio' | 'performance' | 'strategy' | 'transactions' | 'decisions';

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
        <div className="text-gray-500">Loading agent...</div>
      </div>
    );
  }

  if (agentError || !agent) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">
          {agentError?.message || 'Agent not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="agent-page">
      <style>{`
        .agent-page {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        }

        .agent-header {
          margin-bottom: 2rem;
          padding-bottom: 1.5rem;
          border-bottom: 2px solid #E5E7EB;
        }

        .agent-title-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.75rem;
        }

        .agent-title {
          font-size: 2rem;
          font-weight: 700;
          color: #111827;
        }

        .agent-status-badge {
          padding: 0.375rem 0.875rem;
          border-radius: 0.375rem;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .agent-status-badge.active {
          background: #D1FAE5;
          color: #065F46;
        }

        .agent-status-badge.eliminated {
          background: #FEE2E2;
          color: #991B1B;
        }

        .agent-id {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.875rem;
          color: #6B7280;
        }

        /* Tabs */
        .tabs-container {
          border-bottom: 1px solid #E5E7EB;
          margin-bottom: 2rem;
        }

        .tabs-list {
          display: flex;
          gap: 2rem;
        }

        .tab-button {
          padding: 0.75rem 0;
          border: none;
          background: none;
          font-size: 0.9375rem;
          font-weight: 600;
          color: #6B7280;
          cursor: pointer;
          position: relative;
          transition: color 0.15s ease;
        }

        .tab-button:hover {
          color: #374151;
        }

        .tab-button.active {
          color: #007F5F;
        }

        .tab-button.active::after {
          content: '';
          position: absolute;
          bottom: -1px;
          left: 0;
          right: 0;
          height: 2px;
          background: #007F5F;
        }

        /* Tab Content */
        .tab-content {
          animation: fadeIn 0.2s ease;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .loading-state {
          text-align: center;
          padding: 3rem;
          color: #9CA3AF;
        }
      `}</style>

      {/* Agent Header */}
      <div className="agent-header">
        <div className="agent-title-row">
          <h1 className="agent-title">{agent.name}</h1>
          <span className={`agent-status-badge ${agent.status}`}>
            {agent.status}
          </span>
        </div>
        <div className="agent-id">{agent.agent_id}</div>
      </div>

      {/* Tabs */}
      <div className="tabs-container">
        <div className="tabs-list">
          <button
            className={`tab-button ${activeTab === 'portfolio' ? 'active' : ''}`}
            onClick={() => setActiveTab('portfolio')}
          >
            Portfolio
          </button>
          <button
            className={`tab-button ${activeTab === 'performance' ? 'active' : ''}`}
            onClick={() => setActiveTab('performance')}
          >
            Performance
          </button>
          <button
            className={`tab-button ${activeTab === 'strategy' ? 'active' : ''}`}
            onClick={() => setActiveTab('strategy')}
          >
            Strategy
          </button>
          <button
            className={`tab-button ${activeTab === 'transactions' ? 'active' : ''}`}
            onClick={() => setActiveTab('transactions')}
          >
            Transactions
          </button>
          <button
            className={`tab-button ${activeTab === 'decisions' ? 'active' : ''}`}
            onClick={() => setActiveTab('decisions')}
          >
            Decisions
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'portfolio' && (
          <div>
            <div style={{ marginBottom: '2rem' }}>
              <PositionAllocationChart portfolio={agent.portfolio} />
            </div>
            <PortfolioBreakdown portfolio={agent.portfolio} metrics={agent.metrics} />
          </div>
        )}

        {activeTab === 'performance' && (
          <>
            {performanceLoading ? (
              <div className="loading-state">Loading performance data...</div>
            ) : performance?.data_points && experiment ? (
              <AgentPerformanceChart
                dataPoints={performance.data_points}
                agentId={agent.agent_id}
                agentName={agent.name}
                startingCapital={experiment.starting_capital}
              />
            ) : (
              <div className="loading-state">No performance data available</div>
            )}
          </>
        )}

        {activeTab === 'strategy' && (
          <>
            {strategyLoading ? (
              <div className="loading-state">Loading strategy...</div>
            ) : strategy ? (
              <StrategyPanel strategy={strategy} />
            ) : (
              <div className="loading-state">No strategy data available</div>
            )}
          </>
        )}

        {activeTab === 'transactions' && (
          <>
            {transactionsLoading ? (
              <div className="loading-state">Loading transactions...</div>
            ) : transactions ? (
              <TransactionHistory history={transactions} />
            ) : (
              <div className="loading-state">No transaction data available</div>
            )}
          </>
        )}

        {activeTab === 'decisions' && (
          <>
            {decisionsLoading ? (
              <div className="loading-state">Loading decisions...</div>
            ) : decisions ? (
              <DecisionLog
                experimentId={experimentId || ''}
                agentId={agentId || ''}
                decisions={decisions}
              />
            ) : (
              <div className="loading-state">No decision data available</div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
