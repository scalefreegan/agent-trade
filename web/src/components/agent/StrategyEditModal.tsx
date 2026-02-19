import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import type { AgentStrategy, StrategyEditInput } from '../../api/types';

interface StrategyEditModalProps {
  open: boolean;
  strategy: AgentStrategy;
  onClose: () => void;
  onSave: (data: StrategyEditInput) => void;
  isPending: boolean;
  error: string | null;
}

const RISK_OPTIONS = ['conservative', 'moderate', 'aggressive'] as const;

export function StrategyEditModal({
  open,
  strategy,
  onClose,
  onSave,
  isPending,
  error,
}: StrategyEditModalProps) {
  const [philosophy, setPhilosophy] = useState('');
  const [riskTolerance, setRiskTolerance] = useState<string>('');
  const [preferredSectors, setPreferredSectors] = useState('');
  const [timeHorizon, setTimeHorizon] = useState('');
  const [keyMetrics, setKeyMetrics] = useState('');
  const [rationale, setRationale] = useState('');

  useEffect(() => {
    if (open) {
      setPhilosophy(strategy.thesis.philosophy);
      setRiskTolerance(strategy.thesis.risk_tolerance);
      setPreferredSectors(strategy.thesis.preferred_sectors.join(', '));
      setTimeHorizon(strategy.thesis.time_horizon);
      setKeyMetrics(strategy.thesis.key_metrics.join(', '));
      setRationale(strategy.rationale);
    }
  }, [open, strategy]);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const original = strategy.thesis;
    const payload: StrategyEditInput = {};

    if (philosophy !== original.philosophy) payload.philosophy = philosophy;
    if (riskTolerance !== original.risk_tolerance)
      payload.risk_tolerance = riskTolerance as StrategyEditInput['risk_tolerance'];

    const newSectors = preferredSectors.split(',').map((s) => s.trim()).filter(Boolean);
    if (JSON.stringify(newSectors) !== JSON.stringify(original.preferred_sectors))
      payload.preferred_sectors = newSectors;

    if (timeHorizon !== original.time_horizon) payload.time_horizon = timeHorizon;

    const newMetrics = keyMetrics.split(',').map((s) => s.trim()).filter(Boolean);
    if (JSON.stringify(newMetrics) !== JSON.stringify(original.key_metrics))
      payload.key_metrics = newMetrics;

    if (rationale !== strategy.rationale) payload.rationale = rationale;

    if (Object.keys(payload).length === 0) {
      onClose();
      return;
    }
    onSave(payload);
  };

  if (!open) return null;

  const inputClass =
    'w-full px-3 py-2.5 text-sm font-mono bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded transition-colors outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600 focus:ring-2 focus:ring-brand-700 focus:border-brand-700 dark:focus:ring-brand-600 dark:focus:border-brand-600';
  const labelClass =
    'block text-xs font-mono font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400 mb-1.5';

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="strategy-edit-title"
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-2xl bg-white dark:bg-gray-900 shadow-2xl border border-gray-200 dark:border-gray-700 rounded overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="bg-brand-900 px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div>
            <p className="text-xs font-mono text-brand-400 uppercase tracking-widest mb-0.5">
              Strategy
            </p>
            <h2 id="strategy-edit-title" className="text-lg font-semibold text-white tracking-tight">
              Edit Investment Thesis
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-brand-300 hover:text-white transition-colors p-1 rounded"
            aria-label="Close"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M2 2l14 14M16 2L2 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} noValidate className="flex flex-col min-h-0">
          <div className="px-6 pt-6 pb-4 space-y-5 overflow-y-auto">
            {error && (
              <div className="rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 px-4 py-3">
                <p className="text-sm text-red-700 dark:text-red-400 font-mono">{error}</p>
              </div>
            )}

            {/* Philosophy */}
            <div>
              <label htmlFor="strat-philosophy" className={labelClass}>Philosophy</label>
              <textarea
                id="strat-philosophy"
                rows={3}
                value={philosophy}
                onChange={(e) => setPhilosophy(e.target.value)}
                className={`${inputClass} resize-y`}
              />
            </div>

            {/* Risk Tolerance + Time Horizon */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="strat-risk" className={labelClass}>Risk Tolerance</label>
                <select
                  id="strat-risk"
                  value={riskTolerance}
                  onChange={(e) => setRiskTolerance(e.target.value)}
                  className={inputClass}
                >
                  {RISK_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt.charAt(0).toUpperCase() + opt.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="strat-horizon" className={labelClass}>Time Horizon</label>
                <input
                  id="strat-horizon"
                  type="text"
                  value={timeHorizon}
                  onChange={(e) => setTimeHorizon(e.target.value)}
                  placeholder="e.g. 6-12 months"
                  className={inputClass}
                />
              </div>
            </div>

            {/* Preferred Sectors */}
            <div>
              <label htmlFor="strat-sectors" className={labelClass}>Preferred Sectors</label>
              <input
                id="strat-sectors"
                type="text"
                value={preferredSectors}
                onChange={(e) => setPreferredSectors(e.target.value)}
                placeholder="e.g. Technology, Healthcare, Energy"
                className={inputClass}
              />
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-600 font-mono">Comma-separated</p>
            </div>

            {/* Key Metrics */}
            <div>
              <label htmlFor="strat-metrics" className={labelClass}>Key Metrics</label>
              <input
                id="strat-metrics"
                type="text"
                value={keyMetrics}
                onChange={(e) => setKeyMetrics(e.target.value)}
                placeholder="e.g. P/E ratio, Revenue growth, Free cash flow"
                className={inputClass}
              />
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-600 font-mono">Comma-separated</p>
            </div>

            {/* Rationale */}
            <div>
              <label htmlFor="strat-rationale" className={labelClass}>Rationale</label>
              <textarea
                id="strat-rationale"
                rows={3}
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                className={`${inputClass} resize-y`}
              />
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end gap-3 flex-shrink-0">
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              className="px-4 py-2 text-sm font-mono text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="px-5 py-2 text-sm font-mono font-semibold rounded bg-brand-700 hover:bg-brand-800 text-white disabled:opacity-60 disabled:cursor-not-allowed transition-colors flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2"
            >
              {isPending && (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              )}
              {isPending ? 'Saving…' : 'Save Strategy'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
