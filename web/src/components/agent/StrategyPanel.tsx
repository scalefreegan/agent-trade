import type { AgentStrategy } from '../../api/types';

interface StrategyPanelProps {
  strategy: AgentStrategy;
}

export function StrategyPanel({ strategy }: StrategyPanelProps) {
  return (
    <div className="strategy-panel">
      <style>{`
        .strategy-panel {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        }

        .thesis-card {
          background: white;
          border: 1px solid #E5E7EB;
          border-radius: 0.5rem;
          padding: 1.5rem;
          margin-bottom: 2rem;
        }

        .thesis-header {
          display: flex;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .thesis-badge {
          background: #007F5F;
          color: white;
          padding: 0.375rem 0.875rem;
          border-radius: 0.375rem;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .thesis-horizon {
          background: #F3F4F6;
          color: #374151;
          padding: 0.375rem 0.875rem;
          border-radius: 0.375rem;
          font-size: 0.75rem;
          font-weight: 500;
        }

        .thesis-rationale {
          color: #374151;
          line-height: 1.6;
          margin-bottom: 1rem;
        }

        .principles-list {
          list-style: none;
          padding: 0;
          margin: 0;
          display: grid;
          gap: 0.5rem;
        }

        .principle-item {
          display: flex;
          align-items: flex-start;
          gap: 0.5rem;
          color: #374151;
          font-size: 0.875rem;
        }

        .principle-bullet {
          color: #2B9348;
          font-weight: bold;
          flex-shrink: 0;
        }

        .learnings-section {
          margin-top: 2rem;
        }

        .learnings-header {
          font-size: 0.75rem;
          font-weight: 700;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: #007F5F;
          margin-bottom: 1rem;
          padding-bottom: 0.75rem;
          border-bottom: 2px solid #007F5F;
        }

        .learnings-timeline {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .learning-card {
          background: white;
          border: 1px solid #E5E7EB;
          border-radius: 0.5rem;
          padding: 1.25rem;
          position: relative;
          padding-left: 3rem;
        }

        .learning-date {
          position: absolute;
          left: 1rem;
          top: 1.25rem;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.6875rem;
          color: #9CA3AF;
          transform: rotate(-90deg);
          transform-origin: left top;
          white-space: nowrap;
        }

        .learning-outcome-badge {
          display: inline-block;
          padding: 0.25rem 0.625rem;
          border-radius: 0.25rem;
          font-size: 0.6875rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 0.75rem;
        }

        .learning-outcome-badge.positive {
          background: #D1FAE5;
          color: #065F46;
        }

        .learning-outcome-badge.negative {
          background: #FEE2E2;
          color: #991B1B;
        }

        .learning-outcome-badge.neutral {
          background: #FEF3C7;
          color: #92400E;
        }

        .learning-observation {
          color: #374151;
          font-size: 0.875rem;
          line-height: 1.5;
          margin-bottom: 0.5rem;
        }

        .learning-lesson {
          color: #6B7280;
          font-size: 0.8125rem;
          line-height: 1.5;
          font-style: italic;
          padding-left: 1rem;
          border-left: 3px solid #2B9348;
        }

        .empty-learnings {
          text-align: center;
          padding: 2rem;
          color: #9CA3AF;
          font-size: 0.875rem;
        }
      `}</style>

      {/* Investment Thesis Card */}
      <div className="thesis-card">
        <div className="thesis-header">
          <div className="thesis-badge">{strategy.thesis.risk_tolerance}</div>
          <div className="thesis-horizon">{strategy.thesis.time_horizon}</div>
        </div>

        <div className="thesis-rationale">
          <strong>Philosophy:</strong> {strategy.thesis.philosophy}
        </div>

        {strategy.thesis.preferred_sectors.length > 0 && (
          <div className="thesis-rationale" style={{ marginTop: '1rem' }}>
            <strong>Preferred Sectors:</strong> {strategy.thesis.preferred_sectors.join(', ')}
          </div>
        )}

        {strategy.thesis.key_metrics.length > 0 && (
          <>
            <div style={{ marginTop: '1rem', fontSize: '0.75rem', fontWeight: 600, color: '#6B7280', textTransform: 'uppercase' }}>
              Key Metrics
            </div>
            <ul className="principles-list">
              {strategy.thesis.key_metrics.map((metric, idx) => (
                <li key={idx} className="principle-item">
                  <span className="principle-bullet">•</span>
                  <span>{metric}</span>
                </li>
              ))}
            </ul>
          </>
        )}

        <div className="thesis-rationale" style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #E5E7EB' }}>
          <strong>Rationale:</strong> {strategy.rationale}
        </div>
      </div>

      {/* Learnings Timeline */}
      <div className="learnings-section">
        <div className="learnings-header">
          Strategy Learnings ({strategy.learnings.length})
        </div>

        {strategy.learnings.length === 0 ? (
          <div className="empty-learnings">No learnings recorded yet</div>
        ) : (
          <div className="learnings-timeline">
            {strategy.learnings.map((learning, idx) => (
              <div key={idx} className="learning-card">
                <div className="learning-date">{learning.date}</div>
                <div
                  className={`learning-outcome-badge ${
                    learning.outcome.toLowerCase()
                  }`}
                >
                  {learning.outcome}
                </div>
                <div className="learning-observation">{learning.observation}</div>
                <div className="learning-lesson">{learning.lesson}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
