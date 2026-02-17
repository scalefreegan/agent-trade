import { useState } from 'react';
import type { Portfolio, PortfolioMetrics } from '../../api/types';

interface PortfolioBreakdownProps {
  portfolio: Portfolio;
  metrics: PortfolioMetrics;
}

export function PortfolioBreakdown({ portfolio, metrics }: PortfolioBreakdownProps) {
  const [expandedPosition, setExpandedPosition] = useState<string | null>(null);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const calculateHoldingPeriod = (purchaseDate: string) => {
    const now = new Date();
    const purchase = new Date(purchaseDate);
    const days = Math.floor((now.getTime() - purchase.getTime()) / (1000 * 60 * 60 * 24));
    return days;
  };

  const positions = Object.values(portfolio.positions);

  return (
    <div className="portfolio-breakdown">
      <style>{`
        .portfolio-breakdown {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
          --brand-900: #007F5F;
          --brand-800: #2B9348;
          --brand-700: #55A630;
          --brand-600: #80B918;
          --brand-500: #AACC00;
          --gain-color: #2B9348;
          --loss-color: #DC2626;
          --border: #E5E7EB;
          --bg-surface: #FFFFFF;
          --bg-hover: #F9FAFB;
          --text-primary: #111827;
          --text-secondary: #6B7280;
          --text-tertiary: #9CA3AF;
        }

        /* Metrics Grid */
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .metric-card {
          background: var(--bg-surface);
          border: 1px solid var(--border);
          padding: 1.25rem;
          position: relative;
          overflow: hidden;
          transition: all 0.2s ease;
        }

        .metric-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 3px;
          background: linear-gradient(90deg, var(--brand-900), var(--brand-600));
          opacity: 0;
          transition: opacity 0.2s ease;
        }

        .metric-card:hover::before {
          opacity: 1;
        }

        .metric-label {
          font-size: 0.6875rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--text-tertiary);
          margin-bottom: 0.5rem;
        }

        .metric-value {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 1.75rem;
          font-weight: 600;
          color: var(--text-primary);
          line-height: 1.2;
          letter-spacing: -0.02em;
        }

        .metric-value.gain {
          color: var(--gain-color);
        }

        .metric-value.loss {
          color: var(--loss-color);
        }

        .metric-secondary {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.875rem;
          color: var(--text-secondary);
          margin-top: 0.375rem;
        }

        /* Positions Section */
        .positions-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
          padding-bottom: 0.75rem;
          border-bottom: 2px solid var(--brand-900);
        }

        .positions-title {
          font-size: 0.75rem;
          font-weight: 700;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--brand-900);
        }

        .positions-count {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.75rem;
          color: var(--text-tertiary);
          font-weight: 500;
        }

        /* Positions Table */
        .positions-table {
          width: 100%;
          border-collapse: separate;
          border-spacing: 0;
          margin-bottom: 1rem;
        }

        .positions-table thead th {
          text-align: left;
          font-size: 0.6875rem;
          font-weight: 600;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          color: var(--text-tertiary);
          padding: 0.75rem 1rem;
          border-bottom: 1px solid var(--border);
          background: var(--bg-hover);
        }

        .positions-table thead th:first-child {
          border-top-left-radius: 0.375rem;
        }

        .positions-table thead th:last-child {
          border-top-right-radius: 0.375rem;
        }

        .position-row {
          cursor: pointer;
          transition: all 0.15s ease;
          border-bottom: 1px solid var(--border);
        }

        .position-row:hover {
          background: var(--bg-hover);
        }

        .position-row.expanded {
          background: var(--bg-hover);
        }

        .position-row td {
          padding: 1rem;
          font-size: 0.875rem;
        }

        .symbol-cell {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .expand-icon {
          width: 16px;
          height: 16px;
          color: var(--text-tertiary);
          transition: transform 0.2s ease;
          flex-shrink: 0;
        }

        .position-row.expanded .expand-icon {
          transform: rotate(90deg);
        }

        .symbol {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-weight: 700;
          font-size: 0.9375rem;
          color: var(--text-primary);
          letter-spacing: -0.01em;
        }

        .numeric-cell {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.875rem;
          color: var(--text-primary);
          text-align: right;
          tabular-nums;
        }

        .gain-cell {
          color: var(--gain-color);
          font-weight: 600;
        }

        .loss-cell {
          color: var(--loss-color);
          font-weight: 600;
        }

        /* Tax Lots Expandable Section */
        .tax-lots-row {
          background: linear-gradient(to bottom, #F9FAFB 0%, #FFFFFF 100%);
          border-bottom: 1px solid var(--border);
        }

        .tax-lots-container {
          padding: 1.5rem 1rem 1.5rem 3rem;
          animation: slideDown 0.2s ease;
        }

        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .tax-lots-header {
          font-size: 0.6875rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--brand-800);
          margin-bottom: 0.75rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .tax-lots-badge {
          background: var(--brand-900);
          color: white;
          padding: 0.125rem 0.5rem;
          border-radius: 1rem;
          font-size: 0.625rem;
          font-weight: 600;
        }

        .tax-lots-table {
          width: 100%;
          border-collapse: collapse;
          background: white;
          border: 1px solid var(--border);
          border-radius: 0.375rem;
          overflow: hidden;
        }

        .tax-lots-table thead th {
          text-align: left;
          font-size: 0.625rem;
          font-weight: 600;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          color: var(--text-secondary);
          padding: 0.625rem 1rem;
          background: white;
          border-bottom: 1px solid var(--border);
        }

        .tax-lots-table tbody td {
          padding: 0.75rem 1rem;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 0.8125rem;
          color: var(--text-primary);
          border-bottom: 1px solid #F3F4F6;
        }

        .tax-lots-table tbody tr:last-child td {
          border-bottom: none;
        }

        .tax-lots-table tbody tr:hover {
          background: #FAFBFC;
        }

        .holding-period-badge {
          display: inline-flex;
          align-items: center;
          padding: 0.25rem 0.625rem;
          border-radius: 0.25rem;
          font-size: 0.75rem;
          font-weight: 600;
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        }

        .holding-period-badge.long-term {
          background: #D1FAE5;
          color: #065F46;
        }

        .holding-period-badge.short-term {
          background: #FEF3C7;
          color: #92400E;
        }

        /* Cash Row */
        .cash-row {
          background: linear-gradient(90deg, rgba(0, 127, 95, 0.02) 0%, transparent 100%);
          border-bottom: 2px solid var(--border);
        }

        .cash-row td {
          font-weight: 600;
        }

        /* Empty State */
        .empty-state {
          text-align: center;
          padding: 3rem 1rem;
          color: var(--text-tertiary);
        }

        .empty-state-icon {
          width: 48px;
          height: 48px;
          margin: 0 auto 1rem;
          opacity: 0.3;
        }

        .empty-state-text {
          font-size: 0.875rem;
          font-weight: 500;
        }
      `}</style>

      {/* Metrics Grid */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Total Value</div>
          <div className="metric-value">{formatCurrency(metrics.total_value)}</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Unrealized Gain</div>
          <div className={`metric-value ${metrics.unrealized_gain >= 0 ? 'gain' : 'loss'}`}>
            {formatCurrency(metrics.unrealized_gain)}
          </div>
          <div className="metric-secondary">{formatPercent(metrics.unrealized_gain_pct)}</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Cash</div>
          <div className="metric-value">{formatCurrency(portfolio.cash)}</div>
          <div className="metric-secondary">{metrics.cash_pct.toFixed(1)}% of portfolio</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Invested</div>
          <div className="metric-value">
            {formatCurrency(metrics.total_value - portfolio.cash)}
          </div>
          <div className="metric-secondary">{metrics.invested_pct.toFixed(1)}% of portfolio</div>
        </div>
      </div>

      {/* Positions Header */}
      <div className="positions-header">
        <div className="positions-title">Holdings</div>
        <div className="positions-count">
          {positions.length} position{positions.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Positions Table */}
      {positions.length === 0 ? (
        <div className="empty-state">
          <svg className="empty-state-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          <div className="empty-state-text">No positions held</div>
        </div>
      ) : (
        <table className="positions-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th style={{ textAlign: 'right' }}>Shares</th>
              <th style={{ textAlign: 'right' }}>Avg Cost</th>
              <th style={{ textAlign: 'right' }}>Current Price</th>
              <th style={{ textAlign: 'right' }}>Current Value</th>
              <th style={{ textAlign: 'right' }}>Gain/Loss</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => {
              const isExpanded = expandedPosition === position.symbol;
              const gainLoss = position.unrealized_gain || 0;
              const gainLossPct = position.current_value
                ? ((gainLoss / (position.current_value - gainLoss)) * 100)
                : 0;

              return (
                <>
                  <tr
                    key={position.symbol}
                    className={`position-row ${isExpanded ? 'expanded' : ''}`}
                    onClick={() => setExpandedPosition(isExpanded ? null : position.symbol)}
                  >
                    <td>
                      <div className="symbol-cell">
                        <svg className="expand-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                        <span className="symbol">{position.symbol}</span>
                      </div>
                    </td>
                    <td className="numeric-cell">{position.total_shares.toFixed(4)}</td>
                    <td className="numeric-cell">{formatCurrency(position.total_cost_basis)}</td>
                    <td className="numeric-cell">
                      {position.current_price ? formatCurrency(position.current_price) : '—'}
                    </td>
                    <td className="numeric-cell">
                      {position.current_value ? formatCurrency(position.current_value) : '—'}
                    </td>
                    <td className={`numeric-cell ${gainLoss >= 0 ? 'gain-cell' : 'loss-cell'}`}>
                      {position.unrealized_gain !== null ? (
                        <>
                          {formatCurrency(gainLoss)}
                          <div style={{ fontSize: '0.75rem', marginTop: '0.125rem' }}>
                            {formatPercent(gainLossPct)}
                          </div>
                        </>
                      ) : '—'}
                    </td>
                  </tr>

                  {/* Tax Lots Expandable */}
                  {isExpanded && (
                    <tr className="tax-lots-row">
                      <td colSpan={6}>
                        <div className="tax-lots-container">
                          <div className="tax-lots-header">
                            Tax Lots
                            <span className="tax-lots-badge">{position.lots.length}</span>
                          </div>
                          <table className="tax-lots-table">
                            <thead>
                              <tr>
                                <th>Shares</th>
                                <th>Cost Basis</th>
                                <th>Purchase Date</th>
                                <th>Holding Period</th>
                              </tr>
                            </thead>
                            <tbody>
                              {position.lots.map((lot, idx) => {
                                const holdingDays = calculateHoldingPeriod(lot.purchase_date);
                                const isLongTerm = holdingDays >= 365;
                                return (
                                  <tr key={idx}>
                                    <td>{lot.shares.toFixed(4)}</td>
                                    <td>{formatCurrency(lot.cost_basis)}</td>
                                    <td>{formatDate(lot.purchase_date)}</td>
                                    <td>
                                      <span className={`holding-period-badge ${isLongTerm ? 'long-term' : 'short-term'}`}>
                                        {holdingDays} day{holdingDays !== 1 ? 's' : ''}
                                      </span>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}

            {/* Cash Row */}
            <tr className="cash-row">
              <td>
                <div className="symbol-cell">
                  <svg className="expand-icon" style={{ opacity: 0 }} fill="none" viewBox="0 0 24 24">
                    <path d="M9 5l7 7-7 7" />
                  </svg>
                  <span className="symbol">CASH</span>
                </div>
              </td>
              <td className="numeric-cell">—</td>
              <td className="numeric-cell">—</td>
              <td className="numeric-cell">—</td>
              <td className="numeric-cell">{formatCurrency(portfolio.cash)}</td>
              <td className="numeric-cell">—</td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}
