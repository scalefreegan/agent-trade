import { useState } from 'react';
import Markdown from 'react-markdown';
import type { DecisionLogEntry } from '../../api/types';
import { useAgentDecision } from '../../api/agents';

interface DecisionLogProps {
  experimentId: string;
  agentId: string;
  decisions: DecisionLogEntry[];
}

export function DecisionLog({ experimentId, agentId, decisions }: DecisionLogProps) {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const { data: decisionDetail } = useAgentDecision(
    experimentId,
    agentId,
    selectedDate || ''
  );

  return (
    <div className="decision-log">
      <style>{`
        .decision-log {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        }

        .decisions-list {
          display: grid;
          gap: 0.75rem;
          margin-bottom: 1.5rem;
        }

        .decision-card {
          background: white;
          border: 1px solid #E5E7EB;
          border-radius: 0.5rem;
          padding: 1rem 1.25rem;
          cursor: pointer;
          transition: all 0.15s ease;
          display: grid;
          grid-template-columns: auto 1fr auto;
          align-items: center;
          gap: 1rem;
        }

        .decision-card:hover {
          border-color: #2B9348;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .decision-card.selected {
          border-color: #007F5F;
          background: #F0FDF4;
        }

        .decision-date-col {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .decision-date {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.9375rem;
          font-weight: 700;
          color: #111827;
        }

        .decision-day {
          font-size: 0.6875rem;
          color: #6B7280;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .decision-info {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .order-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.375rem;
          padding: 0.25rem 0.625rem;
          border-radius: 0.25rem;
          font-size: 0.6875rem;
          font-weight: 600;
        }

        .order-badge.has-orders {
          background: #D1FAE5;
          color: #065F46;
        }

        .order-badge.no-orders {
          background: #F3F4F6;
          color: #6B7280;
        }

        .decision-arrow {
          width: 20px;
          height: 20px;
          color: #9CA3AF;
          transition: transform 0.2s ease;
        }

        .decision-card:hover .decision-arrow {
          color: #2B9348;
          transform: translateX(4px);
        }

        /* Modal */
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 50;
          padding: 1rem;
          animation: fadeIn 0.2s ease;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .modal-content {
          background: white;
          border-radius: 0.75rem;
          max-width: 900px;
          width: 100%;
          max-height: 90vh;
          display: flex;
          flex-direction: column;
          animation: slideUp 0.3s ease;
        }

        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem;
          border-bottom: 1px solid #E5E7EB;
        }

        .modal-title {
          font-size: 1.125rem;
          font-weight: 700;
          color: #111827;
        }

        .modal-close {
          width: 32px;
          height: 32px;
          border-radius: 0.375rem;
          border: none;
          background: #F3F4F6;
          color: #6B7280;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.15s ease;
        }

        .modal-close:hover {
          background: #E5E7EB;
          color: #374151;
        }

        .modal-body {
          overflow-y: auto;
          padding: 1.5rem;
        }

        /* react-markdown styles */
        .markdown-content {
          font-size: 0.9375rem;
          line-height: 1.7;
          color: #374151;
        }

        .markdown-content h1 {
          font-size: 1.5rem;
          font-weight: 700;
          color: #111827;
          margin: 1.5rem 0 1rem;
          border-bottom: 2px solid #E5E7EB;
          padding-bottom: 0.5rem;
        }

        .markdown-content h2 {
          font-size: 1.25rem;
          font-weight: 600;
          color: #111827;
          margin: 1.25rem 0 0.75rem;
          border-bottom: 1px solid #F3F4F6;
          padding-bottom: 0.375rem;
        }

        .markdown-content h3 {
          font-size: 1.0625rem;
          font-weight: 600;
          color: #111827;
          margin: 1rem 0 0.5rem;
        }

        .markdown-content h4, .markdown-content h5, .markdown-content h6 {
          font-weight: 600;
          color: #111827;
          margin: 0.875rem 0 0.5rem;
        }

        .markdown-content p {
          margin: 0.75rem 0;
        }

        .markdown-content ul, .markdown-content ol {
          margin: 0.75rem 0;
          padding-left: 1.5rem;
        }

        .markdown-content li {
          margin: 0.375rem 0;
        }

        .markdown-content li > p {
          margin: 0.25rem 0;
        }

        .markdown-content code {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          background: #F3F4F6;
          padding: 0.125rem 0.375rem;
          border-radius: 0.25rem;
          font-size: 0.875rem;
        }

        .markdown-content pre {
          background: #F9FAFB;
          border: 1px solid #E5E7EB;
          border-radius: 0.375rem;
          padding: 1rem;
          overflow-x: auto;
          margin: 1rem 0;
        }

        .markdown-content pre code {
          background: none;
          padding: 0;
        }

        .markdown-content blockquote {
          border-left: 4px solid #2B9348;
          padding-left: 1rem;
          margin: 1rem 0;
          color: #6B7280;
          font-style: italic;
        }

        .markdown-content a {
          color: #2B9348;
          text-decoration: underline;
        }

        .markdown-content a:hover {
          color: #007F5F;
        }

        .markdown-content table {
          width: 100%;
          border-collapse: collapse;
          margin: 1rem 0;
        }

        .markdown-content table th,
        .markdown-content table td {
          border: 1px solid #E5E7EB;
          padding: 0.5rem;
          text-align: left;
        }

        .markdown-content table th {
          background: #F9FAFB;
          font-weight: 600;
        }

        .markdown-content hr {
          border: none;
          border-top: 1px solid #E5E7EB;
          margin: 1.5rem 0;
        }

        .empty-state {
          text-align: center;
          padding: 3rem;
          color: #9CA3AF;
        }
      `}</style>

      {decisions.length === 0 ? (
        <div className="empty-state">No decisions recorded yet</div>
      ) : (
        <div className="decisions-list">
          {decisions.map((decision) => (
            <div
              key={decision.date}
              className={`decision-card ${selectedDate === decision.date ? 'selected' : ''}`}
              onClick={() => setSelectedDate(decision.date)}
            >
              <div className="decision-date-col">
                <div className="decision-date">{decision.date}</div>
                <div className="decision-day">Day {decision.trading_day}</div>
              </div>

              <div className="decision-info">
                <div className={`order-badge ${decision.has_orders ? 'has-orders' : 'no-orders'}`}>
                  {decision.has_orders ? (
                    <>
                      ✓ {decision.order_count} order{decision.order_count !== 1 ? 's' : ''}
                    </>
                  ) : (
                    'No orders'
                  )}
                </div>
              </div>

              <svg className="decision-arrow" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          ))}
        </div>
      )}

      {/* Decision Detail Modal */}
      {selectedDate && decisionDetail && (
        <div className="modal-overlay" onClick={() => setSelectedDate(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">Decision for {selectedDate}</div>
              <button
                className="modal-close"
                onClick={() => setSelectedDate(null)}
                aria-label="Close"
              >
                <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="modal-body">
              <div className="markdown-content">
                <Markdown>
                  {decisionDetail.markdown}
                </Markdown>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
