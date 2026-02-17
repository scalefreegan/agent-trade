import { useState } from 'react';
import type { TransactionHistory as TransactionHistoryType } from '../../api/types';

interface TransactionHistoryProps {
  history: TransactionHistoryType;
}

export function TransactionHistory({ history }: TransactionHistoryProps) {
  const [currentPage, setCurrentPage] = useState(0);
  const pageSize = 20;

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const totalPages = Math.ceil(history.transactions.length / pageSize);
  const startIdx = currentPage * pageSize;
  const endIdx = startIdx + pageSize;
  const currentTransactions = history.transactions.slice(startIdx, endIdx);

  return (
    <div className="transaction-history">
      <style>{`
        .transaction-history {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        }

        .summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .summary-card {
          background: white;
          border: 1px solid #E5E7EB;
          padding: 1rem;
          border-radius: 0.375rem;
        }

        .summary-label {
          font-size: 0.6875rem;
          font-weight: 600;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          color: #9CA3AF;
          margin-bottom: 0.5rem;
        }

        .summary-value {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-size: 1.25rem;
          font-weight: 600;
          color: #111827;
        }

        .transactions-table {
          width: 100%;
          border-collapse: collapse;
          background: white;
          border: 1px solid #E5E7EB;
          border-radius: 0.5rem;
          overflow: hidden;
        }

        .transactions-table thead th {
          text-align: left;
          font-size: 0.6875rem;
          font-weight: 600;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          color: #6B7280;
          padding: 0.75rem 1rem;
          background: #F9FAFB;
          border-bottom: 1px solid #E5E7EB;
        }

        .transactions-table tbody td {
          padding: 0.875rem 1rem;
          font-size: 0.875rem;
          border-bottom: 1px solid #F3F4F6;
        }

        .transactions-table tbody tr:last-child td {
          border-bottom: none;
        }

        .transactions-table tbody tr:hover {
          background: #FAFBFC;
        }

        .action-badge {
          display: inline-block;
          padding: 0.25rem 0.625rem;
          border-radius: 0.25rem;
          font-size: 0.6875rem;
          font-weight: 700;
          letter-spacing: 0.05em;
        }

        .action-badge.buy {
          background: #D1FAE5;
          color: #065F46;
        }

        .action-badge.sell {
          background: #DBEAFE;
          color: #1E40AF;
        }

        .symbol-cell {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          font-weight: 700;
          color: #111827;
        }

        .numeric-cell {
          font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
          text-align: right;
          color: #111827;
        }

        .pagination {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 1rem;
          padding: 1rem;
          background: #F9FAFB;
          border-radius: 0.375rem;
        }

        .pagination-info {
          font-size: 0.875rem;
          color: #6B7280;
        }

        .pagination-buttons {
          display: flex;
          gap: 0.5rem;
        }

        .pagination-button {
          padding: 0.5rem 1rem;
          border: 1px solid #E5E7EB;
          background: white;
          color: #374151;
          font-size: 0.875rem;
          font-weight: 500;
          border-radius: 0.375rem;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .pagination-button:hover:not(:disabled) {
          background: #F9FAFB;
          border-color: #D1D5DB;
        }

        .pagination-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .empty-state {
          text-align: center;
          padding: 3rem;
          color: #9CA3AF;
        }
      `}</style>

      {/* Summary Cards */}
      <div className="summary-grid">
        <div className="summary-card">
          <div className="summary-label">Total Transactions</div>
          <div className="summary-value">{history.transactions.length}</div>
        </div>
        <div className="summary-card">
          <div className="summary-label">Buy Volume</div>
          <div className="summary-value">{formatCurrency(history.total_buy_volume)}</div>
        </div>
        <div className="summary-card">
          <div className="summary-label">Sell Volume</div>
          <div className="summary-value">{formatCurrency(history.total_sell_volume)}</div>
        </div>
        <div className="summary-card">
          <div className="summary-label">Total Tax Paid</div>
          <div className="summary-value">{formatCurrency(history.total_tax_paid)}</div>
        </div>
      </div>

      {/* Transactions Table */}
      {history.transactions.length === 0 ? (
        <div className="empty-state">No transactions yet</div>
      ) : (
        <>
          <table className="transactions-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Action</th>
                <th>Symbol</th>
                <th style={{ textAlign: 'right' }}>Shares</th>
                <th style={{ textAlign: 'right' }}>Price</th>
                <th style={{ textAlign: 'right' }}>Total</th>
                <th style={{ textAlign: 'right' }}>Tax</th>
              </tr>
            </thead>
            <tbody>
              {currentTransactions.map((txn, idx) => (
                <tr key={idx}>
                  <td>{txn.date}</td>
                  <td>
                    <span className={`action-badge ${txn.action.toLowerCase()}`}>
                      {txn.action}
                    </span>
                  </td>
                  <td className="symbol-cell">{txn.symbol}</td>
                  <td className="numeric-cell">{txn.shares.toFixed(4)}</td>
                  <td className="numeric-cell">{formatCurrency(txn.price)}</td>
                  <td className="numeric-cell">{formatCurrency(txn.total)}</td>
                  <td className="numeric-cell">
                    {txn.tax_paid !== null ? formatCurrency(txn.tax_paid) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <div className="pagination-info">
                Page {currentPage + 1} of {totalPages} ({history.transactions.length} total)
              </div>
              <div className="pagination-buttons">
                <button
                  className="pagination-button"
                  onClick={() => setCurrentPage(currentPage - 1)}
                  disabled={currentPage === 0}
                >
                  Previous
                </button>
                <button
                  className="pagination-button"
                  onClick={() => setCurrentPage(currentPage + 1)}
                  disabled={currentPage === totalPages - 1}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
